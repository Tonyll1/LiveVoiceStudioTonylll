from core.app import Application


def main():
    app = Application()
    app.setup()
    app.run()


if __name__ == "__main__":
    main()