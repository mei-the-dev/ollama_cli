#!/usr/bin/env python3

def check_todo_fixme(repo_path):
    """
    This function checks for TODO or FIXME comments in all Python files within the given repository path.
    It returns a report with the file paths and line numbers where these comments are found.
    
    :param repo_path: The root directory of the repository to check.
    :return: A dictionary containing the report.
    """
    import os
    import re
    
    # Regular expression to find TODO or FIXME comments
    todo_fixme_pattern = re.compile(r'\b(TODO|FIXME)\b', re.IGNORECASE)
    
    report = {}
    
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                    for line_number, line in enumerate(lines, start=1):
                        if todo_fixme_pattern.search(line):
                            if file_path not in report:
                                report[file_path] = []
                            report[file_path].append(line_number)
    
    return report

if __name__ == '__main__':
    repo_path = '/path/to/your/repo'
    result = check_todo_fixme(repo_path)
    for file, lines in result.items():
        print(f'File: {file}')
        for line_number in lines:
            print(f'  Line {line_number}: Contains TODO or FIXME')