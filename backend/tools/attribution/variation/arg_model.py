# VariationArgModel.py
from typing import List, Dict, Any, Type, Union
from pydantic import BaseModel, Field, create_model
from tools.attribution.variation.analyzer import VariationBasedIndicatorSpec, VariationBasedIndicatorsBlock
from tools.attribution.utils import name_to_snake_key

config_example = ["真时丽收入", "高值品收入", "..."]

class VariationArgModel:
    def __init__(
        self,
        model_name_root: str,
        indicators_config: List[str]
    ):
        """
        初始化
        :param model_name_root: 参数模型命名词根, 采用Pascal Case
        :param indicators_config: 基于变化率分析的参数模型指标配置
            - 示例：
            ["真时丽产品均价", "二合一产品均价", "..."]
        """
        self.model_name_root = model_name_root
        self.indicators_config: List[str] = indicators_config
        self.processed_config = self._create_indicators_config()
        # 缓存属性初始化
        self._cached_args_model4llm = None
        self._cached_args_model = None

    def _create_indicators_config(self) -> List[Dict[str, Any]]:
        """
        创建结构化配置
        :return processed_config:
            - 示例：
            [
            {
                "indicator_name": "真时丽产品均价",
                "indicator_key": "zhen_shi_li_chan_pin_ping_jun_jia"
            },
            {
                "indicator_name": "二合一产品均价",
                "indicator_key": "er_he_yi_chan_pin_ping_jun_jia"
            }
            ]
        """
        processed_config = []
        for indicator in self.indicators_config:
            processed_config.append({
                "indicator_name": indicator,
                "indicator_key": name_to_snake_key(indicator)
            })
        return processed_config

    def create_args_model4llm(self) -> Type[BaseModel]:
        """
        创建LLM输入参数模型
        :return args_model4llm:
            - 示例：
            BaseModel(
                indicators_config=List[Dict[str, Any]]
            )
        """
        # 如果已经创建过，直接返回缓存的模型
        if self._cached_args_model4llm is not None:
            return self._cached_args_model4llm

        fields_4llm = {}
        for config in self.processed_config:
            indicator_name = config.get("indicator_name", "未命名指标")
            indicator_key = config.get("indicator_key", name_to_snake_key(indicator_name))
            fields_4llm[f"{indicator_key}_current"] = (
                Union[float, int],
                Field(..., description=f"{indicator_name}的当前值")
            )
            fields_4llm[f"{indicator_key}_prior"] = (
                Union[float, int],
                Field(..., description=f"{indicator_name}的上期值")
            )
        # 创建并缓存模型
        class_name = f"{self.model_name_root}DataInput4LLM"
        self._cached_args_model4llm = create_model(class_name, **fields_4llm, __base__=BaseModel)
        return self._cached_args_model4llm

    def create_args_model(self) -> Type[BaseModel]:
        """
        创建参数模型
        将LLM输入转换为VariationBasedIndicatorSpec对象
        :return args_model: 内部输入模型类
        """
        # 如果已经创建过，直接返回缓存的模型
        if self._cached_args_model is not None:
            return self._cached_args_model

        # 创建指标字段
        fields = {}
        for config in self.processed_config:
            indicator_name = config.get("indicator_name", "未命名指标")
            indicator_key = config.get("indicator_key", name_to_snake_key(indicator_name))
            fields[indicator_key] = (
                VariationBasedIndicatorSpec,
                Field(..., description=f"{indicator_name}指标")
            )
        def from_llm(cls, llm_input: BaseModel) -> BaseModel:
            """从LLM输入转换为内部输入模型"""
            indicators = {}
            for config in cls.config:
                _indicator_name = config.get("indicator_name", "未命名指标")
                _indicator_key = config.get("indicator_key", name_to_snake_key(_indicator_name))
                indicators[_indicator_key] = VariationBasedIndicatorSpec(
                    indicator_name=_indicator_name,
                    current_value=getattr(llm_input, f"{_indicator_key}_current"),
                    prior_value=getattr(llm_input, f"{_indicator_key}_prior")
                )
            return cls(**indicators)

        # 创建模型类
        class_name = f"{self.model_name_root}DataInput"
        input_para_model_class = create_model(class_name, **fields, __base__=BaseModel)
        # 注入类属性和类方法
        input_para_model_class.config = self.processed_config
        input_para_model_class.from_llm = classmethod(from_llm)
        # 模型缓存
        self._cached_args_model = input_para_model_class
        return self._cached_args_model

    def get_llm_input_schema(self) -> Dict[str, Any]:
        """
        获取LLM输入参数模型的schema信息
        包括参数名称、类型、描述等，用于查看LLM调用函数时看到的参数结构

        :return: 包含参数schema信息的字典
        """
        llm_input_class = self.create_args_model4llm()
        schema = llm_input_class.model_json_schema()

        # 提取并格式化参数信息
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        schema_info = {
            "class_name": schema.get("title", llm_input_class.__name__),
            "description": schema.get("description", ""),
            "parameters": {}
        }

        # 从模型字段注解中获取类型信息
        model_fields = llm_input_class.model_fields

        for param_name, param_info in properties.items():
            # 尝试从字段注解中获取类型
            param_type = "unknown"
            if param_name in model_fields:
                field_info = model_fields[param_name]
                field_type = field_info.annotation

                # 处理 Union 类型
                if hasattr(field_type, '__origin__'):
                    origin = field_type.__origin__
                    # 检查是否是 Union 类型
                    if origin is Union or (hasattr(origin, '__name__') and origin.__name__ == 'Union'):
                        # 获取 Union 中的类型参数
                        args = getattr(field_type, '__args__', [])
                        type_names = []
                        for arg in args:
                            if hasattr(arg, '__name__'):
                                type_names.append(arg.__name__)
                            elif arg == float:
                                type_names.append("float")
                            elif arg == int:
                                type_names.append("int")
                            else:
                                type_names.append(str(arg))
                        if type_names:
                            param_type = "|".join(type_names)
                    elif hasattr(origin, '__name__'):
                        param_type = origin.__name__
                elif hasattr(field_type, '__name__'):
                    param_type = field_type.__name__
                elif field_type == float:
                    param_type = "float"
                elif field_type == int:
                    param_type = "int"
                else:
                    param_type = str(field_type)

            # 如果从字段注解中获取失败，尝试从 JSON schema 中获取
            if param_type == "unknown":
                # 检查是否有 anyOf 结构（Union 类型在 JSON schema 中的表示）
                if "anyOf" in param_info:
                    any_of = param_info["anyOf"]
                    type_names = []
                    for item in any_of:
                        item_type = item.get("type")
                        if item_type == "number":
                            type_names.append("float")
                        elif item_type == "integer":
                            type_names.append("int")
                        elif item_type:
                            type_names.append(item_type)
                    if type_names:
                        param_type = "|".join(type_names)
                # 检查是否有 type 字段
                elif "type" in param_info:
                    schema_type = param_info["type"]
                    if schema_type == "number":
                        param_type = "float|int"
                    else:
                        param_type = schema_type
                else:
                    param_type = param_info.get("type", "unknown")

            schema_info["parameters"][param_name] = {
                "type": param_type,
                "description": param_info.get("description", ""),
                "required": param_name in required
            }

        return schema_info

    def get_internal_input_schema(self) -> Dict[str, Any]:
        """
        获取内部输入参数模型的schema信息
        包括参数名称、类型、描述等

        :return: 包含参数schema信息的字典
        """
        internal_input_class = self.create_args_model()
        schema = internal_input_class.model_json_schema()

        # 提取并格式化参数信息
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        definitions = schema.get("$defs", {})  # Pydantic v2 使用 $defs

        schema_info = {
            "class_name": schema.get("title", internal_input_class.__name__),
            "description": schema.get("description", ""),
            "parameters": {}
        }

        # 从模型字段注解中获取类型信息
        model_fields = internal_input_class.model_fields

        for param_name, param_info in properties.items():
            # 尝试从字段注解中获取类型
            param_type = "unknown"
            if param_name in model_fields:
                field_info = model_fields[param_name]
                # 获取字段的实际类型
                field_type = field_info.annotation
                if hasattr(field_type, '__name__'):
                    param_type = field_type.__name__
                elif hasattr(field_type, '__origin__'):
                    # 处理泛型类型
                    origin = field_type.__origin__
                    if hasattr(origin, '__name__'):
                        param_type = origin.__name__
                else:
                    param_type = str(field_type)

            # 如果从字段注解中获取失败，尝试从 JSON schema 中获取
            if param_type == "unknown":
                # 检查是否有 $ref 引用
                if "$ref" in param_info:
                    ref_path = param_info["$ref"]
                    # 提取引用的类型名（例如 "#/$defs/VariationBasedIndicatorSpec" -> "VariationBasedIndicatorSpec"）
                    if "/" in ref_path:
                        param_type = ref_path.split("/")[-1]
                    else:
                        param_type = ref_path
                # 检查是否有 allOf 结构
                elif "allOf" in param_info:
                    all_of = param_info["allOf"]
                    for item in all_of:
                        if "$ref" in item:
                            ref_path = item["$ref"]
                            if "/" in ref_path:
                                param_type = ref_path.split("/")[-1]
                                break
                # 如果是对象类型，尝试从 definitions 中查找
                elif param_info.get("type") == "object":
                    # 查找是否有对应的定义
                    for def_name, def_info in definitions.items():
                        if def_info == param_info:
                            param_type = def_name
                            break
                    if param_type == "unknown":
                        param_type = "object"
                else:
                    param_type = param_info.get("type", "unknown")

            schema_info["parameters"][param_name] = {
                "type": param_type,
                "description": param_info.get("description", ""),
                "required": param_name in required
            }

        return schema_info

    def print_all_schemas(self) -> None:
        """
        打印所有参数模型的schema信息（包括LLM输入和内部输入）
        格式化输出，便于阅读
        """
        llm_schema = self.get_llm_input_schema()
        internal_schema = self.get_internal_input_schema()

        # 打印LLM输入参数模型
        print("\n" + "=" * 90)
        print(f"[LLM输入参数模型] {llm_schema['class_name']}")
        print("=" * 90)
        if llm_schema['description']:
            print(f"描述: {llm_schema['description']}\n")

        if llm_schema['parameters']:
            print("参数列表:")
            print("-" * 90)
            # 表头
            header = f"{'参数名称':<40} {'类型':<25} {'必填':<10} {'描述'}"
            print(header)
            print("-" * 90)

            # 参数行
            for param_name, param_info in llm_schema['parameters'].items():
                required_mark = "[必填]" if param_info['required'] else "[可选]"
                param_type = param_info['type']
                description = param_info['description']
                # 截断过长的描述
                if len(description) > 35:
                    description = description[:32] + "..."
                print(f"{param_name:<40} {param_type:<25} {required_mark:<10} {description}")
        else:
            print("无参数")

        print("=" * 90)

        # 打印内部输入参数模型
        print("\n" + "=" * 90)
        print(f"[内部输入参数模型] {internal_schema['class_name']}")
        print("=" * 90)
        if internal_schema['description']:
            print(f"描述: {internal_schema['description']}\n")

        if internal_schema['parameters']:
            print("参数列表:")
            print("-" * 90)
            # 表头
            header = f"{'参数名称':<40} {'类型':<25} {'必填':<10} {'描述'}"
            print(header)
            print("-" * 90)

            # 参数行
            for param_name, param_info in internal_schema['parameters'].items():
                required_mark = "[必填]" if param_info['required'] else "[可选]"
                param_type = param_info['type']
                description = param_info['description']
                # 截断过长的描述
                if len(description) > 35:
                    description = description[:32] + "..."
                print(f"{param_name:<40} {param_type:<25} {required_mark:<10} {description}")
        else:
            print("无参数")

        print("=" * 90 + "\n")

    def create_indicators_input_block(
            self,
            input_data: BaseModel
    ) -> VariationBasedIndicatorsBlock:
        """
        从内部输入模型创建 VariationBasedIndicatorsBlock
        用于进行变化率归因分析

        :param input_data: 内部输入模型实例（通过 from_llm 方法从 LLM 输入转换得到）
        :return: VariationBasedIndicatorsBlock 对象

        使用示例：
            # 1. 创建模型
            model_creator = VariationArgModel(
                model_name_root="Chapter3YoY",
                indicators_config=["真时丽产品均价", "二合一产品均价"]
            )

            # 2. 从 LLM 输入创建内部输入模型
            llm_input_class = model_creator.create_args_model4llm()
            internal_input_class = model_creator.create_args_model()

            # 3. LLM 输入数据
            llm_input = llm_input_class(
                zhen_shi_li_chan_pin_ping_jun_jia_current=105.5,
                zhen_shi_li_chan_pin_ping_jun_jia_prior=100.0,
                er_he_yi_chan_pin_ping_jun_jia_current=95.2,
                er_he_yi_chan_pin_ping_jun_jia_prior=98.0
            )

            # 4. 转换为内部输入模型
            internal_input = internal_input_class.from_llm(llm_input)

            # 5. 创建 VariationBasedIndicatorsBlock
            indicators_block = model_creator.create_indicators_input_block(
                input_data=internal_input
            )

            # 6. 使用 VariationBasedAttrAnalyzer 进行归因分析
            from .VariationBasedAttrAnalyzer import VariationBasedAttrAnalyzer
            analyzer = VariationBasedAttrAnalyzer()
            result = analyzer.evaluate_indicators(indicators_block)
        """
        # 验证输入数据是否为正确的内部输入模型类型
        internal_input_class = self.create_args_model()
        if not isinstance(input_data, internal_input_class):
            raise TypeError(
                f"期望 {internal_input_class.__name__} 类型的输入数据，"
                f"但得到 {type(input_data).__name__}"
            )

        # 提取所有指标的 VariationBasedIndicatorSpec 列表
        indicators = []
        for config in self.processed_config:
            indicator_key = config.get("indicator_key")
            indicator = getattr(input_data, indicator_key)
            if not isinstance(indicator, VariationBasedIndicatorSpec):
                raise TypeError(
                    f"指标 {indicator_key} 应该是 VariationBasedIndicatorSpec 类型，"
                    f"但得到 {type(indicator).__name__}"
                )
            indicators.append(indicator)

        # 创建并返回 VariationBasedIndicatorsBlock
        return VariationBasedIndicatorsBlock(indicators=indicators)


# 测试代码示例
if __name__ == "__main__":
    print("=" * 90)
    print("VariationArgModel 功能测试")
    print("=" * 90 + "\n")

    # 测试配置：基于变化率的指标
    test_config = [
        "真时丽产品均价",
        "二合一产品均价",
        "五合一产品均价"
    ]

    # 创建参数模型
    model_creator = VariationArgModel(
        model_name_root="Chapter3YoY",
        indicators_config=test_config
    )

    print("1. 参数模型创建成功！\n")

    # 打印所有schema信息
    print("2. 打印参数模型Schema信息：")
    print("-" * 90)
    model_creator.print_all_schemas()

    # 获取LLM输入模型和内部输入模型
    llm_input_class = model_creator.create_args_model4llm()
    internal_input_class = model_creator.create_args_model()

    print("3. 创建LLM输入实例：")
    print("-" * 90)

    # 测试数据 - 动态生成字段名（模拟实际使用场景）
    # 注意：实际使用时LLM会根据schema自动填充，无需手动指定字段名
    test_data_values = [
        ("真时丽产品均价", 105.5, 100.0),  # (指标名, 当期值, 上期值)
        ("二合一产品均价", 95.2, 98.0),
        ("五合一产品均价", 88.5, 92.0)
    ]

    # 动态构建llm_input_data
    llm_input_data = {}
    for indicator_name, current_val, prior_val in test_data_values:
        # 使用processed_config获取正确的indicator_key
        config = next((c for c in model_creator.processed_config
                      if c["indicator_name"] == indicator_name), None)
        if config:
            indicator_key = config["indicator_key"]
            llm_input_data[f"{indicator_key}_current"] = current_val
            llm_input_data[f"{indicator_key}_prior"] = prior_val

    print(f"LLM输入数据: {llm_input_data}\n")

    # 创建LLM输入实例
    llm_input_instance = llm_input_class(**llm_input_data)
    print(f"LLM输入实例类型: {type(llm_input_instance).__name__}")
    print(f"LLM输入实例: {llm_input_instance}\n")

    print("4. 转换为内部输入模型：")
    print("-" * 90)

    # 使用 from_llm 方法转换为内部输入模型
    internal_input_instance = internal_input_class.from_llm(llm_input_instance)
    print(f"内部输入实例类型: {type(internal_input_instance).__name__}\n")

    # 打印内部输入实例的每个字段
    for config in model_creator.processed_config:
        indicator_key = config.get("indicator_key")
        indicator_spec = getattr(internal_input_instance, indicator_key)
        print(f"[{indicator_key}]")
        print(f"  - indicator_name: {indicator_spec.indicator_name}")
        print(f"  - current_value: {indicator_spec.current_value}")
        print(f"  - prior_value: {indicator_spec.prior_value}")

    print("\n5. 使用 VariationBasedAttrAnalyzer 进行归因分析：")
    print("-" * 90)

    # 创建 VariationBasedIndicatorsBlock
    indicators_block = model_creator.create_indicators_input_block(
        input_data=internal_input_instance
    )

    # 创建分析器并执行分析
    from tools.attribution.variation.analyzer import VariationBasedAttrAnalyzer
    analyzer = VariationBasedAttrAnalyzer()
    result = analyzer.evaluate_indicators(indicators_block)

    # 打印分析结果
    print(f"\n分析结果概览:")
    print(f"  - 总指标数: {len(result.indicators)}")
    print(f"  - 负向指标数: {len(result.negative_indicators)}")
    print(f"  - 正向指标数: {len(result.positive_indicators)}\n")

    print(f"【负向指标分析】（下降的产品）")
    if result.negative_indicators:
        for idx, indicator_result in enumerate(result.negative_indicators, 1):
            print(f"\n  [{idx}] {indicator_result.indicator_name}")
            print(f"      当期值: {indicator_result.current_value}")
            print(f"      上期值: {indicator_result.prior_value}")
            print(f"      绝对变化: {indicator_result.change_value:+.2f}")
            print(f"      相对变化率: {indicator_result.change_rate:+.2f}%")
            print(f"      变化方向: ↓ 下降")
    else:
        print("  无负向指标")

    print(f"\n【正向指标分析】（上升的产品）")
    if result.positive_indicators:
        for idx, indicator_result in enumerate(result.positive_indicators, 1):
            print(f"\n  [{idx}] {indicator_result.indicator_name}")
            print(f"      当期值: {indicator_result.current_value}")
            print(f"      上期值: {indicator_result.prior_value}")
            print(f"      绝对变化: {indicator_result.change_value:+.2f}")
            print(f"      相对变化率: {indicator_result.change_rate:+.2f}%")
            print(f"      变化方向: ↑ 上升")
    else:
        print("  无正向指标")

    print("\n" + "=" * 90)
    print("测试完成！")
    print("=" * 90)