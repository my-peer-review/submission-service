pipeline {
  agent any

  environment {
    ENV = "test"
    COMPOSE_FILE = "docker-compose.test.yml"
    TEST_SECRETS_PATH = "/home/jenkins_user/secrets/assignment-test"
  }

  stages {

    stage('Setup environment') {
      steps {
        echo "🔧 Copio i secrets nella workspace..."
        sh '''
          cp $TEST_SECRETS_PATH/.env.test .env.test
          mkdir -p secrets
          cp $TEST_SECRETS_PATH/public.pem secrets/public.pem
          cp $TEST_SECRETS_PATH/private.pem secrets/private.pem
        '''
      }
    }

    stage('Build & start test environment') {
      steps {
        sh 'docker-compose -f $COMPOSE_FILE up -d --build'
      }
    }

    stage('Wait for FastAPI to be ready') {
      options { timeout(time: 2, unit: 'MINUTES') }
      steps {
        echo "⏳ Aspetto che FastAPI sia disponibile..."
        sh '''
          set -euo pipefail
          for i in {1..24}; do
            if curl -sf http://localhost:5050/docs > /dev/null; then
              echo "✅ FastAPI è pronta!"
              exit 0
            fi
            echo "⏳ Attendo FastAPI (tentativo $i)..."
            sleep 5
          done
          echo "❌ FastAPI non è pronta entro il tempo previsto."
          exit 1
        '''
      }
    }

    stage('Run API Tests with Newman') {
      steps {
        sh '''
          newman run tests/postman/Assignments.postman_collection.json \
            -e tests/postman/Assignments.postman_environment.json \
            --reporters cli,json
        '''
      }
    }

    stage('Tear down environment') {
      steps {
        sh 'docker-compose -f $COMPOSE_FILE down'
      }
    }
  }

  post {
    always {
      echo "🧼 Pulizia finale..."
      deleteDir() // Pulisce la workspace
    }
    success {
      echo "✅ Build e test completati con successo!"
    }
    failure {
      echo "❌ Qualcosa è andato storto."
    }
  }
}
