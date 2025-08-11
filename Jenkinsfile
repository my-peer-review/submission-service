pipeline {
  agent any

  options {
    ansiColor('xterm')
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
  }

  environment {
    ENV = 'unit-test'
    CI_IMAGE_NAME = 'assignments-pytest'
    APP_IMAGE_NAME = 'tuo-utente/app-image' // es: dockerhubuser/app
    COMMIT = "${env.GIT_COMMIT?.take(7) ?: 'local'}"
  }

  stages {

    stage('Build CI Image') {
      steps {
        echo "Costruzione immagine CI..."
        sh '''
          set -euxo pipefail
          docker build -t "${CI_IMAGE_NAME}" -f Dockerfile.unit .
        '''
      }
    }

    stage('Run Python Unit Tests') {
      steps {
        echo "Esecuzione test Python..."
        sh '''
          set -euxo pipefail
          docker run --rm \
            --user "$(id -u)":"$(id -g)" \
            -e ENV="${ENV}" \
            -v "${PWD}:/work" -w /work \
            "${CI_IMAGE_NAME}" pytest -v test/pytest
        '''
      }
    }

    stage('Build & Push App Image') {
      steps {
        script {
          docker.withRegistry('https://index.docker.io/v1/', 'dockerhub-creds') {
            def appImage = docker.build("${APP_IMAGE_NAME}", "-f Dockerfile .")
            appImage.push("${COMMIT}")
            appImage.push("latest")
          }
        }
      }
    }
  }

  post {
    always {
      sh '''
        set -euxo pipefail
        chmod -R u+rwX .pytest_cache || true
        rm -rf .pytest_cache || true
      '''
      deleteDir()
    }
    success {
      echo "Build, test e push completati con successo!"
    }
    failure {
      echo "Qualcosa è andato storto."
    }
  }
}
