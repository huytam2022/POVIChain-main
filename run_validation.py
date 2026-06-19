import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from research.validation.fidelity import main

if __name__ == "__main__":
    main(sys.argv[1:])
