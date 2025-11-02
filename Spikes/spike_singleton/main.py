from Setting_file import setting_inst
from Cats import Cats

def main():
    print("Hello from spike-singleton!")
    print(f'Setting name: {setting_inst.name}')

    Cats_instance = Cats()
    Cats_instance.name = 'new cat name'

    print(f'Cats instance name: {Cats_instance.name}')
    print(f'Cats instance setting name: {Cats_instance.setting_inst.name}')
 




if __name__ == "__main__":
    main()
