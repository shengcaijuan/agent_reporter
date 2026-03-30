# AddArgModel.py
from typing import Dict, Any, Type, List, Optional, Union
from pydantic import BaseModel, Field, create_model
from tools.attribution.contribution.analyzer import (
    IndicatorSpec,
    DimensionAttributionBlock,
    AttributionRelationType
)
from tools.attribution.utils import (
    snake_to_pascal,
    name_to_snake_key
)

"""输入&配置参数项"""
# 定义子指标配置类型
ChildNameSpec = Union[str, Dict[str, Any]]

def normalize_child_name(child: ChildNameSpec, default_coefficient: float = 1.0) -> tuple[str, float]:
    """
    标准化子指标名称配置
    支持两种格式：
    1. 字符串: "指标名称"
    2. 字典: {"name": "指标名称", "coefficient": 1.0} 或 {"name": "指标名称"}

    :param child: 子指标配置（字符串或字典）
    :param default_coefficient: 默认系数
    :return: (name, coefficient) 元组
    """
    if isinstance(child, str):
        return child, default_coefficient
    elif isinstance(child, dict):
        name = child.get("name")
        if name is None:
            raise ValueError(f"字典格式的子指标配置必须包含 'name' 字段: {child}")
        coefficient = child.get("coefficient", default_coefficient)
        return name, coefficient
    else:
        raise ValueError(f"无效的子指标配置格式: {child}")


"""参数模型构建器"""
class AddDimArgModel:
    """
    加法维度参数模型构建器
    根据指标配置动态创建输入参数模型
    """

    def __init__(
            self,
            parent_indicator_name: str,
            dimension_name: str,
            child_indicator_names: List[ChildNameSpec],
            parent_key: Optional[str] = None,
            dimension_key: Optional[str] = None,
            child_keys: Optional[List[str]] = None,
            default_coefficient: float = 1.0
    ):
        """
        :param parent_indicator_name: 父指标名称（如 "传统渠道收入"）
        :param dimension_name: 维度名称（如 "渠道维度"）
        :param child_indicator_names: 子指标名称列表，支持两种格式：
            - 字符串列表: ["线上渠道收入", "线下渠道收入"]
            - 字典列表: [{"name": "线上渠道收入", "coefficient": 1.0}, {"name": "线下渠道收入"}]
            - 混合格式: ["线上渠道收入", {"name": "线下渠道收入", "coefficient": -1.0}]
        :param parent_key: 父指标键名（可选，如果不提供则自动从parent_name生成）
        :param dimension_key: 维度键名（可选，如果不提供则自动从dimension_name生成）
        :param child_keys: 子指标键名列表（可选，如果不提供则自动从child_indicator_names生成）
        :param default_coefficient: 默认系数（默认为1.0，仅当子指标为字符串时使用）

        使用示例：
            # 1. 全部使用字符串（最简单）
            model = AddDimArgModel(
                parent_indicator_name="传统渠道收入",
                dimension_name="渠道维度",
                child_indicator_names=["线上渠道收入", "线下渠道收入"]
            )

            # 2. 部分使用字典指定 coefficient
            model = AddDimArgModel(
                parent_indicator_name="传统渠道收入",
                dimension_name="渠道维度",
                child_indicator_names=[
                    "线上渠道收入",  # 使用默认 coefficient (1.0)
                    {"name": "线下渠道收入", "coefficient": -1.0},  # 自定义 coefficient
                    {"name": "其他收入"}  # 使用默认 coefficient
                ]
            )

            # 3. 全部使用字典格式
            model = AddDimArgModel(
                parent_indicator_name="传统渠道收入",
                dimension_name="渠道维度",
                child_indicator_names=[
                    {"name": "线上渠道收入", "coefficient": 1.0},
                    {"name": "线下渠道收入", "coefficient": -1.0}
                ]
            )
        """
        self.parent_indicator_name = parent_indicator_name
        self.dimension_name = dimension_name
        self.child_indicator_names = child_indicator_names
        self.parent_key = parent_key
        self.dimension_key = dimension_key
        self.child_keys = child_keys
        self.default_coefficient = default_coefficient
        self.config = self._create_indicators_config()
        # 保留内部使用的扁平化配置，供其他方法使用
        self.indicators_config = self._get_flat_indicators_config()
        # 缓存属性初始化
        self._cached_args_model4llm = None
        self._cached_args_model = None

    def get_dimension_name(self) -> str:
        """
        获取维度名称
        :return: 维度名称
        """
        return self.dimension_name

    def _create_indicators_config(self) -> Dict[str, Any]:
        """
        创建结构化配置
        返回格式：
        {
            "parent_indicator": {"name": "传统渠道收入", "key": "chuan_tong_qu_dao_shou_ru"},
            "dimension_name": "客户维度",
            "child_indicators": [
                {"name": "线上渠道收入", "key": "xian_shang_qu_dao_shou_ru", "coefficient": 1.0},
                ...
            ]
        }
        """
        # 自动生成或使用提供的key
        if self.parent_key is None:
            self.parent_key = name_to_snake_key(self.parent_indicator_name)

        if self.dimension_key is None:
            self.dimension_key = name_to_snake_key(self.dimension_name)

        # 标准化子指标配置并提取名称和系数
        normalized_children = [normalize_child_name(child, self.default_coefficient) for child in
                               self.child_indicator_names]
        child_name_list = [name for name, _ in normalized_children]
        child_coefficient_list = [coef for _, coef in normalized_children]

        # 生成子指标keys
        if self.child_keys is None:
            self.child_keys = [name_to_snake_key(name) for name in child_name_list]

        if len(self.child_keys) != len(child_name_list):
            raise ValueError(f"child_keys长度({len(self.child_keys)})与child_names长度({len(child_name_list)})不匹配")

        # 构建结构化配置
        config = {
            "parent_indicator": {
                "name": self.parent_indicator_name,
                "key": self.parent_key
            },
            "dimension_name": self.dimension_name,
            "child_indicators": [
                {
                    "name": child_name,
                    "key": child_key,
                    "coefficient": child_coefficient
                }
                for child_key, child_name, child_coefficient in
                zip(self.child_keys, child_name_list, child_coefficient_list)
            ]
        }

        return config

    def _get_flat_indicators_config(self) -> Dict[str, Dict[str, Any]]:
        """
        获取扁平化的指标配置（供内部方法使用）
        返回格式：
        {
            "chuan_tong_qu_dao_shou_ru": {"name": "传统渠道收入", "coefficient": 1.0},
            "xian_shang_qu_dao_shou_ru": {"name": "线上渠道收入", "coefficient": 1.0},
            ...
        }
        """
        flat_config: Dict[str, Dict[str, Any]] = {}

        # 添加父指标配置
        parent_info = self.config["parent_indicator"]
        flat_config[parent_info["key"]] = {
            "name": parent_info["name"],
            "coefficient": self.default_coefficient
        }

        # 标准化子指标配置并提取系数
        normalized_children = [normalize_child_name(child, self.default_coefficient) for child in
                               self.child_indicator_names]
        child_coefficient_list = [coef for _, coef in normalized_children]

        # 添加子指标配置
        for child_info, child_coefficient in zip(self.config["child_indicators"], child_coefficient_list):
            flat_config[child_info["key"]] = {
                "name": child_info["name"],
                "coefficient": child_coefficient
            }

        return flat_config

    def create_args_model4llm(self) -> Type[BaseModel]:
        """
        创建LLM输入参数模型
        为每个指标生成 current 和 prior 字段
        :return: LLM输入模型类
        """
        # 如果已经创建过，直接返回缓存的模型
        if self._cached_args_model4llm is not None:
            return self._cached_args_model4llm

        fields_4llm = {}
        for indicator_key, indicator_config in self.indicators_config.items():
            indicator_name: str = indicator_config.get("name", "未命名指标")
            fields_4llm[f"{indicator_key}_current"] = (
                Union[float, int],
                Field(..., description=f"当期{indicator_name}")
            )
            fields_4llm[f"{indicator_key}_prior"] = (
                Union[float, int],
                Field(..., description=f"上期{indicator_name}")
            )

        # 生成类名
        parent_part = snake_to_pascal(self.parent_key)
        dim_part = snake_to_pascal(self.dimension_key)
        class_name = f"{parent_part}{dim_part}DataInput4LLM"

        # 创建并缓存模型
        self._cached_args_model4llm = create_model(class_name, **fields_4llm, __base__=BaseModel)
        return self._cached_args_model4llm

    def create_args_model(self) -> Type[BaseModel]:
        """
        创建内部输入参数模型
        将LLM输入转换为IndicatorSpec对象
        :return: 内部输入模型类
        """
        # 如果已经创建过，直接返回缓存的模型
        if self._cached_args_model is not None:
            return self._cached_args_model

        # 创建指标字段
        fields = {}
        for indicator_key, indicator_config in self.indicators_config.items():
            indicator_name: str = indicator_config.get("name", "未命名指标")
            fields[indicator_key] = (
                IndicatorSpec,
                Field(..., description=f"{indicator_name}指标")
            )

        def from_llm(cls, llm_input: BaseModel) -> BaseModel:
            """从LLM输入转换为内部输入模型"""
            indicators = {}
            for key, cfg in cls.config.items():
                current = getattr(llm_input, f"{key}_current")
                prior = getattr(llm_input, f"{key}_prior")
                coefficient = float(cfg.get("coefficient", 1.0))
                indicators[key] = IndicatorSpec(
                    name=cfg.get("name", key),
                    current_value=current,
                    prior_value=prior,
                    coefficient=coefficient
                )
            return cls(**indicators)

        # 创建模型类
        parent_part = snake_to_pascal(self.parent_key)
        dim_part = snake_to_pascal(self.dimension_key)
        class_name = f"{parent_part}{dim_part}DataInput"
        input_para_model_class = create_model(class_name, **fields, __base__=BaseModel)

        # 注入类属性和类方法
        input_para_model_class.config = self.indicators_config
        input_para_model_class.from_llm = classmethod(from_llm)

        # 创建并缓存模型
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
                    # 提取引用的类型名（例如 "#/$defs/IndicatorSpec" -> "IndicatorSpec"）
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

    def create_dimension_attribution_block(
            self,
            input_data: BaseModel,
            relation_type: AttributionRelationType = AttributionRelationType.ADDITIVE
    ) -> DimensionAttributionBlock:
        """
        从内部输入模型创建 DimensionAttributionBlock
        用于进行维度归因分析

        :param input_data: 内部输入模型实例（通过 from_llm 方法从 LLM 输入转换得到）
        :param relation_type: 维度关系类型（默认加法关系）
        :return: DimensionAttributionBlock 对象

        使用示例：
            # 1. 创建模型
            model = AddDimArgModel(
                parent_indicator_name="收入",
                dimension_name="产品维度",
                child_indicator_names=["真时丽", "二合一", "五合一"]
            )

            # 2. 从 LLM 输入创建内部输入模型
            llm_input_class = model.create_data_input_4_llm_class()
            internal_input_class = model.create_data_input_class()

            # 3. LLM 输入数据
            llm_input = llm_input_class(
                shou_ru_current=1000.0,
                shou_ru_prior=900.0,
                zhen_shi_li_current=300.0,
                zhen_shi_li_prior=270.0,
                # ... 其他子指标
            )

            # 4. 转换为内部输入模型
            internal_input = internal_input_class.from_llm(llm_input)

            # 5. 创建 DimensionAttributionBlock
            dim_block = model.create_dimension_attribution_block(
                input_data=internal_input,
                relation_type=AttributionRelationType.ADDITIVE
            )

            # 6. 使用 AttributionAnalyzer 进行归因分析
            from tools.BasicAttributionModule.AttributionAnalyzer import AttributionAnalyzer
            analyzer = AttributionAnalyzer()
            result = analyzer.dimension_attribution_analysis(dim_block)
        """
        # 验证输入数据是否为正确的内部输入模型类型
        internal_input_class = self.create_args_model()
        if not isinstance(input_data, internal_input_class):
            raise TypeError(
                f"期望 {internal_input_class.__name__} 类型的输入数据，"
                f"但得到 {type(input_data).__name__}"
            )

        # 提取父指标的 IndicatorSpec
        parent_indicator = getattr(input_data, self.parent_key)
        if not isinstance(parent_indicator, IndicatorSpec):
            raise TypeError(
                f"父指标 {self.parent_key} 应该是 IndicatorSpec 类型，"
                f"但得到 {type(parent_indicator).__name__}"
            )

        # 提取子指标的 IndicatorSpec 列表
        sub_indicators = []
        for child_info in self.config["child_indicators"]:
            child_key = child_info["key"]
            child_indicator = getattr(input_data, child_key)
            if not isinstance(child_indicator, IndicatorSpec):
                raise TypeError(
                    f"子指标 {child_key} 应该是 IndicatorSpec 类型，"
                    f"但得到 {type(child_indicator).__name__}"
                )
            sub_indicators.append(child_indicator)

        # 创建并返回 DimensionAttributionBlock
        return DimensionAttributionBlock(
            dim_name=self.dimension_name,
            dim_type=relation_type,
            parent_indicator=parent_indicator,
            sub_indicators=sub_indicators
        )

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


# 测试代码示例
if __name__ == "__main__":
    ModelCreator = AddDimArgModel(
        parent_indicator_name="收入",
        dimension_name="产品维度",
        child_indicator_names=["真时丽收入", "二合一收入", "五合一收入", "艺术漆收入", "腻子粉收入", "鲜呼吸收入",
                               "其他收入"],
    )

    # 方式1: 打印所有schema信息（推荐）
    ModelCreator.print_all_schemas()
