from programmer import ALGORITHM
from forward_testing import FORWARD

f = FORWARD()
a = ALGORITHM()

def testing():
    f.programmer()

def production():
    a.programmer()


def main():
    # production()
    testing()

if __name__ == '__main__':
    main()
