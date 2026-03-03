from web2json import Web2JsonConfig, extract_data

config = Web2JsonConfig(
    name="my_project",
    html_path="input_html/house",
    save=['schema', 'code', 'data'],  # Save to local disk
    # output_path="./results",  # Custom output directory (default: "output")
)

result = extract_data(config)

# Results are always returned in memory
print(result.final_schema)        # Dict: extracted schema
print(result.parser_code)          # str: generated parser code
print(result.parsed_data[0])       # List[Dict]: parsed JSON data