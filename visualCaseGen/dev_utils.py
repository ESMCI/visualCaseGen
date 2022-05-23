
# debug flag, turns on some checks during runtime
debug = True

mode = "dynamic" #or "static"

# List of all ConfigVar assignments in chronological order. Used for debugging purposes
assignment_history = []

class RunError(Exception):

    def __init__(self, message="", print_assignment_hist=True):
        self.message = message
        print("A runtime error encountered. Here is the variable assignment that led to the error:")
        if print_assignment_hist:
            for assignment in assignment_history:
                print(assignment)
        super().__init__(self.message)

