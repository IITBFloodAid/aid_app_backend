from app import create_app

app = create_app()

# below part is for the dev purposes...
if __name__ == '__main__':
    app.run(debug=True)