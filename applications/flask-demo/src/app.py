from flask import Flask
app = Flask(__name__)

@app.route('/')
def demoapp():
  return 'Hello from EKS! This application is built using Github Actions on AWS CodeBuild'

@app.route('/health')
def health():
  return 'ok'

if __name__ == '__main__':
  app.run(port=8080,host='0.0.0.0')
