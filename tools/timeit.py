import time
from functools import wraps


def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result

    return wrapper


def timeit_class(cls):
    """
    Decorator to time all methods in a class.
    """
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and not attr_name.startswith("__"):
            setattr(cls, attr_name, timeit(attr))
    return cls


if __name__ == "__main__":

    @timeit
    def example_function(x, y):
        time.sleep(1)  # Simulate a time-consuming operation
        return x + y

    print(example_function(5, 10))

    @timeit_class
    class ExampleClass:
        def method_one(self):
            time.sleep(0.5)
            return "Method One"

        def method_two(self):
            time.sleep(0.3)
            return "Method Two"

    example = ExampleClass()
    print(example.method_one())
    print(example.method_two())
