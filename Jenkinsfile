pipeline {
  agent any

  stages {

    // UNIT TESTS (ENV=unit-test)
    stage('Unit Tests') {
      environment {
        ENV = 'unit-test'
        IMAGE_NAME = 'assignments-pytest'
      }
      stages {
        stage('Build CI Image') {
          steps {
            echo "Costruzione immagine da Dockerfile.unit..."
            sh '''
              set -eux
              docker build -t "${IMAGE_NAME}" -f Dockerfile.unit .
            '''
          }
        }
        stage('Run Python Unit Tests') {
          steps {
            echo "Avvio container CI per i unit-test..."
            sh '''
              set -eux
              docker run --rm \
                --user "$(id -u)":"$(id -g)" \
                -e ENV="${ENV}" \
                -v "${PWD}:/work" -w /work \
                "${IMAGE_NAME}" pytest -v test/pytest
            '''
          }
        }
      }

      post {
        always {
          sh '''
            set -eux
            chmod -R u+rwX .pytest_cache || true
            rm -rf .pytest_cache || true
          '''
        }
      }
    }


    // INTEGRATION TESTS (ENV=local-integration)
    stage('Integration Tests') {
      options {
        lock(resource: 'ports-for-test-assignment')
      }
      environment {
        ENV = 'local-integration'
        COMPOSE_FILE = 'docker-compose.test.yml'
        TEST_SECRETS_PATH = '/home/jenkins-user/secrets/assignment-test'
        COMPOSE_PROJECT_NAME = "assignments-${env.BUILD_NUMBER}"
      }
      stages {
        stage('Setup environment') {
          steps {
            echo "🔧 Copio i secrets nella workspace..."
            sh '''
              set -eux
              cp "$TEST_SECRETS_PATH/.env.test" .env.test
              mkdir -p secrets
              cp "$TEST_SECRETS_PATH/public.pem" secrets/public.pem
              cp "$TEST_SECRETS_PATH/private.pem" secrets/private.pem
            '''
          }
        }
        stage('Build & start test environment') {
          steps {
            sh '''
              set -eux
              docker compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" up -d --build
            '''
          }
        }
        stage('Run API Tests with Newman') {
          steps {
            sh '''
              set -eux
              newman run ./test/postman/Assignments.postman_collection.json \
                -e ./test/postman/Assignments.postman_environment.json \
                --reporters cli,json
            '''
          }
        }
      }
      post {
        always {
          echo "Pulizia ambiente di integrazione..."
          sh '''
            set -eux
            docker compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" down || true
          '''
          deleteDir()
        }
        success {
          echo "Build e test completati con successo!"
        }
        failure {
          echo "Qualcosa è andato storto."
        }
      }
    }
  }
}
