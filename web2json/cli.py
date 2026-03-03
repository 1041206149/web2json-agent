"""
web2json-agent CLI 入口点
提供 pip 安装后的命令行接口，支持多个子命令
"""
import sys
import argparse
import json
from pathlib import Path
from web2json.config.validator import ConfigValidator, check_config_or_guide


def generate_schema_template_from_fields(field_names: list) -> dict:
    """
    根据字段名列表生成schema模板

    Args:
        field_names: 字段名列表，例如 ['price', 'fuel_economy', 'engine']

    Returns:
        schema模板字典
    """
    schema_template = {}
    for field_name in field_names:
        # 清理字段名，确保是有效的UTF-8字符串
        clean_name = field_name.strip()
        try:
            # 确保字段名可以正确编码为UTF-8
            clean_name = clean_name.encode('utf-8', errors='replace').decode('utf-8')
        except Exception:
            pass

        schema_template[clean_name] = {
            "type": "",
            "description": "",
            "value_sample": "",
            "xpaths": [""]
        }
    return schema_template


def interactive_schema_input() -> dict:
    """
    交互式输入字段名，生成schema模板

    Returns:
        schema模板字典
    """
    import sys

    print("\n" + "="*70)
    print("交互式Schema输入模式")
    print("="*70)
    print("\n请输入需要提取的字段名，用空格分隔")
    print("示例：")
    print("  英文字段（推荐）: price fuel_economy engine model")
    print("  中文字段（支持）: 价格 油耗 引擎 型号")

    while True:
        try:
            # 确保正确处理中文输入
            if sys.stdin.encoding and sys.stdin.encoding.lower() != 'utf-8':
                print(f"⚠️  检测到终端编码为 {sys.stdin.encoding}，建议使用 UTF-8 编码")

            user_input = input("请输入字段名: ")

            # 显式处理编码，确保正确读取中文
            if isinstance(user_input, bytes):
                user_input = user_input.decode('utf-8', errors='replace')

            # 清理替代字符和其他编码问题
            # 这一步很重要，可以避免后续JSON序列化和API调用时的编码错误
            try:
                user_input = user_input.encode('utf-8', errors='replace').decode('utf-8')
            except Exception:
                pass

            user_input = user_input.strip()

            if not user_input:
                print("❌ 输入不能为空，请重新输入")
                continue

            # 按空格分割字段名
            field_names = [name.strip() for name in user_input.split() if name.strip()]

            if not field_names:
                print("❌ 未识别到有效的字段名，请重新输入")
                continue

            # 检查字段名是否有效
            invalid_fields = [f for f in field_names if not f]
            if invalid_fields:
                print("❌ 发现无效的字段名，请重新输入")
                continue

            # 生成schema模板
            schema_template = generate_schema_template_from_fields(field_names)

            # 显示生成的模板
            print("\n生成的Schema模板：")
            print("-"*70)
            # 确保中文正确显示
            print(json.dumps(schema_template, ensure_ascii=False, indent=2))
            print("-"*70)

            # 显示字段列表（便于确认）
            print(f"\n字段列表（{len(field_names)}个）: {', '.join(field_names)}")

            # 确认
            confirm = input("\n确认使用这个Schema模板吗？(y/n): ").strip().lower()
            if confirm in ['y', 'yes', '']:
                print("✓ Schema模板已确认\n")
                return schema_template
            else:
                print("\n重新输入字段名...\n")

        except UnicodeDecodeError as e:
            print(f"❌ 编码错误: {e}")
            print("请确保终端支持UTF-8编码，或使用英文字段名")
            continue
        except Exception as e:
            print(f"❌ 输入错误: {e}")
            print("请重新输入")
            continue


def cmd_init(args):
    """初始化配置文件"""
    print("\n🚀 初始化 web2json-agent 配置\n")

    target_dir = Path(args.dir) if args.dir else Path.cwd()
    env_file = ConfigValidator.create_env_file(target_dir)

    print("\n下一步:")
    print(f"  1. 编辑 {env_file}")
    print("  2. 填入你的 API 密钥（OPENAI_API_KEY 和 OPENAI_API_BASE）")
    print("  3. 运行 'web2json check --test-api' 检查API响应")
    print()


def cmd_setup(args):
    """交互式配置向导"""
    print("\n🚀 web2json-agent 交互式配置\n")
    ConfigValidator.interactive_setup()


def cmd_check(args):
    """检查配置"""
    print("\n🔍 检查配置...\n")
    is_valid, missing = ConfigValidator.check_config(verbose=True)

    if not is_valid:
        print("\n❌ 配置不完整")
        print("\n解决方法:")
        print("  1. 运行 'web2json init' 创建配置文件")
        print("  2. 或运行 'web2json setup' 使用交互式配置向导")
        sys.exit(1)

    # 如果基本配置通过，且用户要求测试 API
    if args.test_api:
        print("\n🔌 测试 API 连接...\n")
        api_valid, errors = ConfigValidator.test_api_connection(test_models=True)

        if not api_valid:
            print("\n❌ API 连接测试失败")
            for model_name, error in errors.items():
                print(f"  ✗ {model_name}: {error}")
            print("\n请检查:")
            print("  1. API 密钥是否正确")
            print("  2. API Base URL 是否可访问")
            print("  3. 模型名称是否正确")
            print("  4. 网络连接是否正常")
            sys.exit(1)

    print("\n✅ 所有检查通过！可以开始使用了")
    print("\n示例命令:")
    print("  web2json -d input_html/ -o output/blog")



def cmd_generate(args):
    """生成解析器（主功能）"""
    # 检查必需的目录参数
    if not args.directory:
        print("\n❌ 错误: 缺少必需的参数 -d/--directory")
        print("\n使用方法:")
        print("  web2json -d input_html/ -o output/blog")
        print("\n运行 'web2json --help' 查看完整帮助")
        sys.exit(1)

    # 在执行主功能前检查配置
    if not args.skip_config_check:
        check_config_or_guide()

    # 导入并执行主程序
    from web2json.main import (
        main as main_func,
        setup_logger,
        read_html_files_from_directory,
        generate_parsers_by_layout_clusters
    )
    from web2json.agent import ParserAgent
    from loguru import logger

    setup_logger()

    logger.info("="*70)
    logger.info("web2json-agent - 智能网页解析代码生成器")
    logger.info("="*70)

    # 处理交互式输入模式
    schema_mode = getattr(args, 'schema_mode', None)
    schema_template = getattr(args, 'schema_template', None)

    if getattr(args, 'interactive_schema', False):
        # 交互式输入模式
        logger.info("启用交互式Schema输入模式")
        schema_template_dict = interactive_schema_input()

        # 自动设置为 predefined 模式
        schema_mode = 'predefined'
        schema_template = schema_template_dict
        logger.info(f"将使用预定义模式，字段: {list(schema_template_dict.keys())}")
    elif schema_template:
        # 如果提供了schema_template文件路径，读取文件
        try:
            template_path = Path(schema_template)
            if not template_path.exists():
                logger.error(f"Schema模板文件不存在: {schema_template}")
                sys.exit(1)

            with open(template_path, 'r', encoding='utf-8') as f:
                schema_template = json.load(f)
            logger.info(f"已加载Schema模板文件: {template_path}")
            logger.info(f"模板字段: {list(schema_template.keys())}")
        except Exception as e:
            logger.error(f"读取Schema模板文件失败: {e}")
            sys.exit(1)

    # 获取HTML文件列表（从目录读取）
    logger.info(f"从目录读取HTML文件: {args.directory}")
    html_files = read_html_files_from_directory(args.directory)
    logger.info(f"读取到 {len(html_files)} 个HTML文件")

    # 根据 cluster 参数选择生成方式
    if getattr(args, 'cluster', False):
        # 按布局聚类分别生成解析器
        logger.info("使用布局聚类模式，将为每个布局簇生成独立的解析器")
        generate_parsers_by_layout_clusters(
            html_files=html_files,
            base_output=args.output,
            domain=args.domain,
        )
        return

    # 创建Agent
    agent = ParserAgent(
        output_dir=args.output,
        enable_schema_edit=getattr(args, 'enable_schema_edit', False)
    )

    # 生成解析器
    result = agent.generate_parser(
        html_files=html_files,
        domain=args.domain,
        iteration_rounds=getattr(args, 'iteration_rounds', None),
        schema_mode=schema_mode,
        schema_template=schema_template,
        enable_schema_edit=getattr(args, 'enable_schema_edit', False)
    )

    # 输出结果
    if result['success']:
        logger.success("\n✓ 解析器生成成功!")
        logger.info(f"  解析器路径: {result['parser_path']}")
        logger.info(f"  配置路径: {result['config_path']}")

    else:
        logger.error("\n✗ 解析器生成失败")
        if 'error' in result:
            logger.error(f"  错误: {result['error']}")
        sys.exit(1)


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog='web2json',
        description='web2json-agent - 智能网页解析代码生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 首次使用：初始化配置
  web2json init
  web2json setup          # 或使用交互式配置向导

  # 检查配置
  web2json check
  web2json check --test-api

  # 从目录读取HTML文件并生成解析器
  web2json -d input_html/ -o output/blog

  # 交互式输入字段名生成解析器
  web2json -d input_html/ -o output/blog --interactive-schema

  # 使用预定义schema模板文件
  web2json -d input_html/ -o output/blog --schema-mode predefined --schema-template schema.json

更多信息: https://github.com/ccprocessor/web2json-agent
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # init 命令
    parser_init = subparsers.add_parser('init', help='初始化配置文件')
    parser_init.add_argument(
        '--dir',
        help='配置文件目录（默认: 当前目录）'
    )
    parser_init.set_defaults(func=cmd_init)

    # setup 命令
    parser_setup = subparsers.add_parser('setup', help='交互式配置向导')
    parser_setup.set_defaults(func=cmd_setup)

    # check 命令
    parser_check = subparsers.add_parser('check', help='检查配置')
    parser_check.add_argument(
        '--test-api',
        action='store_true',
        help='测试 API 连接和模型可用性'
    )
    parser_check.set_defaults(func=cmd_check)

    # 主命令参数（生成解析器）
    parser.add_argument(
        '-d', '--directory',
        help='HTML文件目录路径'
    )
    parser.add_argument(
        '-o', '--output',
        default='output',
        help='输出目录（默认: output）'
    )
    parser.add_argument(
        '--domain',
        help='域名（可选）'
    )
    parser.add_argument(
        '--iteration-rounds',
        type=int,
        help='迭代轮数（用于Schema学习的样本数量，默认: 3）'
    )
    parser.add_argument(
        '--schema-mode',
        choices=['auto', 'predefined'],
        help='Schema模式：auto=自动提取和筛选字段，predefined=使用预定义schema模板（默认: auto）'
    )
    parser.add_argument(
        '--schema-template',
        help='预定义schema模板文件路径（JSON格式，当schema-mode=predefined时必需）'
    )
    parser.add_argument(
        '--interactive-schema',
        action='store_true',
        help='交互式输入模式：提示用户输入需要提取的字段名，自动生成schema模板'
    )
    parser.add_argument(
        '--enable-schema-edit',
        action='store_true',
        help='启用Schema手动编辑模式：在schema生成后暂停，允许用户手动编辑'
    )
    parser.add_argument(
        '--cluster',
        action='store_true',
        help='是否按布局聚类分别生成解析器（默认: 否，使用全部HTML生成单个解析器）'
    )
    parser.add_argument(
        '--skip-config-check',
        action='store_true',
        help='跳过配置检查（用于调试）'
    )

    # 解析参数
    args = parser.parse_args()

    # 如果没有指定子命令，检查是否提供了目录参数
    if args.command is None:
        if args.directory:
            # 当作生成命令处理
            cmd_generate(args)
        else:
            # 显示帮助信息
            parser.print_help()
            print("\n💡 提示: 首次使用请先运行 'web2json init' 或 'web2json setup'")
    else:
        # 执行子命令
        args.func(args)


if __name__ == "__main__":
    main()
