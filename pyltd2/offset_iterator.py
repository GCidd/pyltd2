from typing import Tuple

class OffsetIterator:
    def __init__(self, start: int = 0, step_size: int = 50, default_direction: str = "forward") -> None:
        """Helper class that iterates from start value with a step_size, given a direction.
    
        It is used for the offset parameter and provides an easier and compact way to increase
        the offset value, or decrease it in case the request fails and it needs to go backwards.

        Args:
            start (int, optional): Start of iteration. Defaults to 0.
            step_size (int, optional): Step of iteration. Defaults to 50.
            default_direction (str, optional): Direction of iteration. Defaults to "forward".
            If "forward", then step_size is added to the current step, if "backward" then
            "step_size" is subtracted from the current step.
        """
        self.start = start
        self.current = self.start
        self.step_size = step_size
        self.default_direction = default_direction
    
    def reset(self) -> str:
        """Resets the counters to start.

        Returns:
            str: The __str__ representation of OffsetITerator.
        """
        self.current = self.start
        return str(self)
    
    def step_forward(self) -> str:
        """Performs a forward step.

        Returns:
            str: The __str__ representation of OffsetITerator.
        """
        self.current += self.step_size
        return str(self)
    
    def step_backward(self) -> str:
        """Performs a backward step.

        Returns:
            str: The __str__ representation of OffsetITerator.
        """
        self.current -= self.step_size
        return str(self)
    
    def __str__(self) -> str:
        return f"{self.current}"
    
    def __call__(self, direction: str = None) -> Tuple[str, str]:
        """Depending on the direction, performs the appropriate directional step 
        and returns the value before the step along with the current value.

        Args:
            direction (str, optional): Override the default step direction. Defaults to None.

        Returns:
            str: Value before performing the step.
            str: Value after performing the step.
        """
        previous = self.current
        step = direction if direction is not None else self.default_direction
        if step == "backward":
            self.step_backward()
        elif step == "forward":
            self.step_forward()
        return previous, str(self)
