from typing import List

from apps.adapters.framework.context import ExecutionContext


# ########## DO NOT USE THESE FOR NOW, KEPT FOR FUTURE REFERENCE ONLY #################
# def step_template__using_simple_function(execution_context: ExecutionContext):
#     """
#     A step is simply a function that accepts an execution_context, and performs an action.
#
#     A step defined as a plain function (like this one) is useful for simplistic tasks that do not
#     require parameters.
#     """
#     raise NotImplementedError('This is for documentation only')


# def step_template__using_closure(*args, **kwargs):
#     """
#     For folks who don't like classes - this could also be achieved using closures.
#
#     HOWEVER, DO NOT USE THIS, because we'd eventually like to use these steps as declarative statements
#     (instead of procedural logic), and closures don't provide an easy way to access args/kwargs outside the closure
#     """
#     def _actual_step(execution_context: ExecutionContext):
#         raise NotImplementedError('This is for documentation only')
#
#     return _actual_step


class StepTemplateUsingClass:
    """
    For steps that require configuration/parameters to function correctly, we can use classes
    with __call__ to provide those params to the actual step.
    In this template, args and kwargs will be available to the __call__ method via self

    Example: If your step's logic is to "sleep" for N seconds, you would want to keep N configurable,
    otherwise it would be a pretty rigid / non-reusable function
    """

    def __init__(self, *args, **kwargs):
        """initializer"""
        self.args = args
        self.kwargs = kwargs

    def __call__(self, execution_context: ExecutionContext):
        """actual step function"""
        raise NotImplementedError("This is for documentation only")


class NoOp:
    def __call__(self, execution_context: ExecutionContext):
        """do nothing"""


class Wrap:
    """Wrap args in a step and execute arbitrary logic"""

    def __init__(self, process: callable, value):
        self.process = process
        self.value = value

    def __call__(self, execution_context: ExecutionContext):
        return self.process(execution_context)


class SequentialSteps:
    """Takes in a list of steps, executes them sequentially"""

    def __init__(self, steps: List):
        self.steps = steps

    def __call__(self, execution_context):
        results = []
        for step in self.steps:
            results.append(step(execution_context))
        return results
