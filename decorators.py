from tool.functions import query_stream
from typing import Callable, Any
from functools import wraps
import time
import sys
import os

counter_funcs = []

def timer(func: Callable) -> Callable:
    ''' To measure the execution time of a function '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__}: {end_time - start_time: 0.4f} seconds")
        return result
    return wrapper

def counter(func: Callable) -> Callable:
    '''
    To count the times of a function is called and sum up the execution time, calculate the average execution time

    Usage:
    @ counter
    def f():
        pass

    print_func(f)
    '''
    global counter_funcs
    @wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        wrapper.times += end_time - start_time
        wrapper.avg_time = wrapper.times / wrapper.calls
        return result

    wrapper.calls = 0       # call amount 
    wrapper.times = 0.0     # total execution time
    wrapper.avg_time = 0.0  # average execution time
    for attr in ('__module__', '__name__', '__qualname__', '__doc__'):      # copy function attributes to wrapper
        setattr(wrapper, attr, getattr(func, attr))
        
    counter_funcs.append(wrapper)
    return wrapper

def print_funcs() -> None:
    '''
    Print the information of a function, including call count, total execution time, and average execution time.
    '''
    for func in counter_funcs:
        print(f"Func name: {func.__qualname__}")
        print(f"call count: {func.calls}")
        print(f"total time: {func.times: 0.4f} seconds")
        print(f"average time: {func.avg_time: 0.4f} seconds\n")

import atexit
atexit.register(print_funcs)

def log(desc: str = "") -> Callable:
    '''
    Log the start and the end of a function that is time-consuming.

    :param desc: A description of the function that is being logged.
    '''
    def helper(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            if desc:
                print(f"Starting {desc}...")
            else:
                print(f"Calling  {func.__qualname__}")
            result = func(*args, **kwargs)
            if desc:
                print(f"Finished {desc} in {time.time() - start_time: 0.4f} seconds")
            else:
                print(f"Finished {func.__qualname__} in {time.time() - start_time: 0.4f} seconds")
            return result

        return wrapper

    return helper


def retry(retries: int = 3, delay: float = 1) -> Callable:
    """
    Attempt to call a function, if it fails, try again with a specified delay.

    :param retries: The max amount of retries you want for the function call
    :param delay: The delay (in seconds) between each function retry
    :return:
    """

    # Don't let the user use this decorator if they are high
    if retries < 1 or delay <= 0:
        raise ValueError('Are you high, mate?')

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for i in range(1, retries + 1):  # 1 to retries + 1

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Break out of the loop if the max amount of retries is exceeded
                    print(f'Running ({i}): {func.__name__}()')
                    if i == retries:
                        print(f'Error: {repr(e)}.')
                        print(f'"{func.__qualname__}()" failed after {retries} retries.')
                        break
                    else:
                        print(f'Error: {repr(e)} -> Retrying...')
                        time.sleep(delay)  # Add a delay before running the next iteration

        return wrapper

    return decorator

def handle_exception(func: Callable) -> Callable:
    import traceback
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("Enter Ctrl + C to exit.")
            return None
        except:
            info = traceback.format_exc()
            print(info)
            print("分析报告如下.")
            prompt = f"请一步一步的根据下面的报错信息，分析出错的原因，请忽略Traceback (most recent call last):，以及关于wrapper的报错信息，报错信息如下：\n{info}"
            output = query_stream(prompt, max_tokens=1000, temperature=0.5)
            with open('error.md', 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"分析报告已保存至error.md。")
            return None
    return wrapper

def cache(func):
    ''' Cache the result of a function to avoid recomputing the result if the same input. '''
    cache_ = {}
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items()))) 
        if key in cache_: 
            return cache_[key]
        else:
            result = func(*args, **kwargs) 
            cache_[key] = result 
            return result
    
    return wrapper

def trace(func):
    '''
    Usage:
        Trace the input and output of a function.

    Example:
        @trace
        def add(a, b):
            return a + b

        add(1, 2)
        # Output:
        # Calling "add" with:
        #   Positional arguments: [1, 2]
        #   Keyword arguments: {}
        # 3
        # Execution time: 0.0001 seconds
    '''

    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling \"{func.__name__}\" with:")
        print(f"  Positional arguments: {list(args)}")
        print(f"  Keyword arguments: {kwargs}")

        start_time = time.time()

        result = func(*args, **kwargs)

        end_time = time.time()
        elapsed_time = end_time - start_time

        print(f"{func.__name__} returned: {result}")
        print(f"Execution time: {elapsed_time:.4f} seconds\n")

        return result
    
    return wrapper

def redirect(log_file: str):
    '''
    Usage:
        Redirect the stdout to a file.

    Parameters:
        :log_file: the path of the output file.

    Returns:
        A decorator that redirects the stdout to a file.

    Example:
        @redirect('output.log')
        def my_func(a, b):
            print(a+b)
    '''
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            original_stdout = sys.stdout
            
            dirname = os.path.dirname(log_file)
            if dirname and not os.path.exists(dirname):
                os.mkdir(os.path.dirname(log_file))
            
            with open(log_file, 'a') as log:
                sys.stdout = log
                try:
                    result = func(*args, **kwargs)
                finally:
                    sys.stdout = original_stdout
            
            return result
        return wrapper
    return decorator