from PySide2 import QtWidgets, QtCore


class Template:
    def __init__(self, *args):
        print("Init Template {}".format(args))
        super().__init__(*args)
        pass
    def hey(self):
        print("Using Template")


class ConcreteBase:
    def __init__(self, *args):
        print("Init Concrete {}".format(args))
        # super().__init__()
        pass

    def hey(self):
        print("Using concrete swapped class {}".format(self.__class__.__name__))


class Child(Template):
    def __init__(self, *args):
        super().__init__(*args)

    def hey(self):
        super().hey()
        print("Running Child Class")


def createView(parent, child, *args, **kwargs):
    new_class = type('NewClass', (child, parent), dict(child.__dict__))
    this = new_class(*args, **kwargs)
    return this





if __name__ == '__main__':
    this = createView(ConcreteBase, Child, "Barf")
    this.hey()