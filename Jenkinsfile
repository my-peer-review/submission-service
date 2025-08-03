pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo "🔹 Sto eseguendo la pipeline di prova per il repository ${env.JOB_NAME}"
                echo "🔹 Branch corrente: ${env.BRANCH_NAME}"
                checkout scm
            }
        }

        stage('Environment Info') {
            steps {
                echo "✅ Jenkins esegue sul nodo: ${env.NODE_NAME}"
                echo "✅ Workspace: ${env.WORKSPACE}"
                echo "✅ Branch rilevato: ${env.BRANCH_NAME}"
            }
        }

        stage('List Files') {
            steps {
                sh 'echo "Contenuto del repository:" && ls -al'
            }
        }

        stage('Fake Build') {
            steps {
                echo "🏗️ Finta build completata per il branch ${env.BRANCH_NAME}"
            }
        }
    }

    post {
        success {
            echo "🎉 Pipeline di prova completata con successo!"
        }
        failure {
            echo "❌ Qualcosa è andato storto nella pipeline di prova."
        }
    }
}
