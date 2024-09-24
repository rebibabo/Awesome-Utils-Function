import os
import sys
import json
from tqdm import tqdm
from loguru import logger
from typing import List, Union, Callable, Any
from concurrent.futures import ThreadPoolExecutor


def load_jsonl(file_path: str) -> list[dict]:
    '''
    Usage:
        Load a jsonl file into a list of dictionaries.
        If the json data is not in a valid jsonl format, it will be skipped.
        There are two possible formats:
            1. Each line is a valid json string.
            Example:
                {"text": "This is a sample text."}
            2. There is a indention of 4 spaces.
            Example:
                {
                    "text": "This is a sample text."
                    "labels": [
                        "label1", 
                        "label2"
                    ]
                }
    
    Parameters:
        :file_path: the path of the jsonl file.

    Returns:
        A list of dictionaries.
    '''
    lines = open(file_path, 'r', encoding='utf-8').readlines()
    if not lines:
        return []
    data_list = []

    try:
        if lines[0] == '{\n':
            json_lines = []
            for line in lines:
                line = line.strip()
                if line:
                    json_lines.append(line)
                
                if line == '}':
                    json_str = ''.join(json_lines)
                    json_obj = json.loads(json_str)
                    data_list.append(json_obj)
                    json_lines = []

        else:
            for line in lines:
                line = line.strip()
                if line:
                    data_list.append(json.loads(line))

    except json.JSONDecodeError as e:
        print(f'Error decoding JSON: {e}')
        data_list = []

    return data_list

def debug(*args, stop=True):
    ''' Print the name, type, and value of a variable. '''
    import inspect
    stack = inspect.stack()
    caller_frame_record = stack[1]
    filename = caller_frame_record.filename
    lineno = caller_frame_record.lineno
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    line = lines[lineno-1].strip().replace(' ', '')
    assert line.startswith("debug")
    left_idx = line.index('(')
    right_idx = line.rindex(')')
    text = line[left_idx+1:right_idx]
    param_names = text.split(',')
    for arg, name in zip(args, param_names):
        print(f'name:  {name}\ntype:  {type(arg)}\nvalue: {arg}\n')
    if stop:
        input()

def get_parser(language):
    ''' Get a tree-sitter parser for a given language. '''
    from tree_sitter import Language, Parser
    if not os.path.exists(f'./build/{language}-languages.so'):
        if not os.path.exists(f'./tree-sitter-{language}'):
            os.system(f'git clone https://github.com/tree-sitter/tree-sitter-{language}')
        Language.build_library(
            f'./build/{language}-languages.so',
            [
                f'./tree-sitter-{language}',
            ]
        )
    LANGUAGE = Language(f'./build/{language}-languages.so', language)
    parser = Parser()
    parser.set_language(LANGUAGE)
    return parser

def get_child(obj, indices: Union[int, List[int]], attribute='children'):
    ''' safely access any tree like object's child node according to the given indices path. '''
    current_node = obj
    if isinstance(indices, int):
        indices = [indices]
    for index in indices:
        try:
            current_node = getattr(current_node, attribute)[index]
        except IndexError:
            logger.warning(f"Index {index} out of range for {attribute}.")
            return None
        except AttributeError:
            logger.exception(f"{obj.__class__.__name__} has no attribute {attribute}.")
            return None
    return current_node

text = lambda x: x.text.decode('utf-8') if x else 'None'
parse = lambda parser, text: parser.parse(bytes(text, 'utf8')).root_node

def query(input, 
    model: str = "gpt-4o-mini-2024-07-18", 
    temperature: float = 0.5, 
    max_tokens: int = 2000, 
    system_prompt: str = "You are a knowledgeable and experienced assistant."
) -> str:
    ''' Query OpenAI API to generate a response to a given input. '''
    from openai import OpenAI
    client = OpenAI()
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input}
        ],
        max_tokens=max_tokens,  
        temperature=temperature
    )

    return completion.choices[0].message.content

def query_stream(input,
    model: str = "gpt-4o-mini-2024-07-18",
    temperature: float = 0.5,
    max_tokens: int = 2000,
    system_prompt: str = "You are a knowledgeable and experienced assistant."
) -> str:
    ''' Query OpenAI API to generate a response to a given input in streaming mode. '''
    from openai import OpenAI
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input}
        ],
        stream=True,  
    )

    output = ''

    for item in response:   
        content = item.choices[0].delta.content
        if content:
            print(content, end='')
            output += content
    print()
    return output

def no_warning():
    ''' Ignore all warnings and handle Ctrl + C simply.'''
    import warnings
    import signal
    warnings.filterwarnings("ignore")
    def signal_handler(signal, frame):
        print("\nEnter Ctrl + C to exit.")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

def run_shell(command: str):
    '''
    ls [dir]
        -r: recursive
        -t [type]: filter by type
    rm [file]: remove file
        -r: recursively remove directory
    cp [src] [dst]: copy file
    mv [src] [dst]: move file
    cd [dir]: change directory
    mkdir [dir]: create directory
        -f: force create directory
    pwd: print current directory
    date: print current date and time
    '''
    import shlex
    import shutil
    import argparse

    args = shlex.split(command)

    if args[0] == 'ls':
        parser = argparse.ArgumentParser(description='Simulate a shell command.')
        parser.add_argument('directory', nargs='?', default='.', help='The directory to list files from')
        parser.add_argument('-r', '--recursive', action='store_true', help='List files recursively')
        parser.add_argument('-t', '--type', nargs='+', help='The type of files to list', default='all')
        args = parser.parse_args(args[1:]) 

        dir = args.directory
        if not os.path.exists(dir):
            print(f"Directory {dir} not found.")
            return
        file_list = []
        if args.recursive:
            for root, dirs, files in os.walk(dir):
                for file in files:
                    file_list.append(os.path.join(root, file))
        else:
            file_list = os.listdir(dir)
            file_list = [os.path.join(dir, file) for file in file_list]
        if args.type!= 'all':
            file_list = [file for file in file_list if os.path.splitext(file)[1][1:] in args.type]
        return file_list

    elif args[0] == 'rm':
        parser = argparse.ArgumentParser(description='Simulate a shell command.')
        parser.add_argument('path', help='The file to remove')
        parser.add_argument('-r', '--recursive', action='store_true', help='Recursively remove directory')
        args = parser.parse_args(args[1:])

        path = args.path
        if not os.path.exists(path):
            print(f"File {path} not found.")
            return False
        if os.path.isdir(path):
            if args.recursive:
                shutil.rmtree(path)
                return True
            else:
                print(f"Directory {path} is not empty. Use -r to remove recursively.")
                return False
        else:
            os.remove(path)
            return True

    elif args[0] == 'cp':
        parser = argparse.ArgumentParser(description='Simulate a shell command.')
        parser.add_argument('src', help='The source file to copy')
        parser.add_argument('dst', help='The destination file or directory')
        args = parser.parse_args(args[1:])

        src = args.src
        dst = args.dst
        if not os.path.exists(src):
            print(f"Source file {src} not found.")
            return False
        if os.path.isdir(src):
            if os.path.exists(dst):
                print(f"Destination {dst} already exists.")
                return False
            shutil.copytree(src, dst)
            return True
        else:
            if os.path.exists(dst):
                print(f"Destination {dst} already exists.")
                return False
            shutil.copy(src, dst)
            return True

    elif args[0] =='mv':
        parser = argparse.ArgumentParser(description='Simulate a shell command.')
        parser.add_argument('src', help='The source file to move')
        parser.add_argument('dst', help='The destination file or directory')
        args = parser.parse_args(args[1:])

        src = args.src
        dst = args.dst
        if not os.path.exists(src):
            print(f"Source file {src} not found.")
            return False
            
        if os.path.isdir(src):
            if os.path.exists(dst):
                print(f"Destination {dst} already exists.")
                return False
            shutil.move(src, dst)
            return True
        else:
            basename = os.path.basename(src)
            if not dst.endswith(basename):
                dst = os.path.join(dst, basename)
            if os.path.exists(dst):
                print(f"Destination {dst} already exists.")
                return False
            shutil.move(src, dst)
            return True

    elif args[0] == 'cd':
        parser = argparse.ArgumentParser(description='Simulate a shell command.')
        parser.add_argument('directory', help='The directory to change to')
        args = parser.parse_args(args[1:])

        dir = args.directory
        if not os.path.exists(dir):
            print(f"Directory {dir} not found.")
            return False
        os.chdir(dir)
        return os.getcwd()

    elif args[0] =='mkdir':
        parser = argparse.ArgumentParser(description='Simulate a shell command.')
        parser.add_argument('directory', help='The directory to create')
        parser.add_argument('-f', '--force', action='store_true', help='Force create directory')
        args = parser.parse_args(args[1:])

        dir = args.directory
        if os.path.exists(dir) and not args.force:
            print(f"Directory {dir} already exists. Use -f to force create directory.")
            return False
        if args.force and os.path.exists(dir):
            shutil.rmtree(dir)
        os.makedirs(dir, exist_ok=True)
        return True

    elif args[0] == 'pwd':
        return os.getcwd()

    elif args[0] == 'date':
        import datetime
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    else:
        print(f"Command {args[0]} not recognized.")
        return False

def run_in_parallel(func: Callable, *args, n: int=8) -> List[Any]:
    '''
    Usage:
        Run a function in parallel.

    Parameters:
        :func: the function to run in parallel.
        :args: the arguments of the function.
        :n: the number of threads to use.
        
    Returns:
        A list of the results of the function.

    Example:
        def add(a, b):
            return a + b

        results = run_in_parallel(add, [1, 2, 3], [4, 5, 6], n=4)
        results = run_in_parallel(add, [1, 2, 3], 2, n=4)   equivalent to run_in_parallel(add, [1, 2, 3], [2, 2, 2], n=4)
    '''

    if len(args) != func.__code__.co_argcount:
        raise ValueError("Number of arguments does not match function signature")
    list_arg_lens = []
    for arg in args:
        if isinstance(arg, list):
            list_arg_lens.append(len(arg))
    if not all(l == list_arg_lens[0] for l in list_arg_lens):
        raise ValueError("All arguments must be lists of the same length")
    new_args = []
    for arg in args:
        if isinstance(arg, list):
            new_args.append(arg)
        else:
            new_args.append([arg]*list_arg_lens[0])
    
    with ThreadPoolExecutor(max_workers=n) as executor:
        results = list(tqdm(executor.map(func, *new_args), total=list_arg_lens[0]))

    return results

