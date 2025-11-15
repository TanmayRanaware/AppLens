pipeline {
  agent any

  options { timestamps(); ansiColor('xterm'); buildDiscarder(logRotator(numToKeepStr: '20')) }

  environment {
    REGISTRY       = 'docker.io'
    FRONTEND_IMAGE = 'tanmayranaware/applens-frontend'
    BACKEND_IMAGE  = 'tanmayranaware/applens-backend'
    EC2_HOST       = 'ubuntu@ec2-3-21-127-72.us-east-2.compute.amazonaws.com' // <— your instance
    TAG            = "${env.BRANCH_NAME}-${env.BUILD_NUMBER}"
  }

  stages {
    stage('Checkout') { steps { checkout scm } }

    stage('Build Images (parallel)') {
      parallel {
        stage('Frontend') { steps { sh "docker build -t ${FRONTEND_IMAGE}:${TAG} -f frontend/Dockerfile frontend" } }
        stage('Backend')  { steps { sh "docker build -t ${BACKEND_IMAGE}:${TAG}  -f backend/Dockerfile  backend" } }
      }
    }

    stage('Login & Push to Docker Hub') {
      steps {
        script {
          docker.withRegistry("https://${env.REGISTRY}", 'dockerhub-creds') {
            sh """
              docker push ${FRONTEND_IMAGE}:${TAG}
              docker push ${BACKEND_IMAGE}:${TAG}
              docker tag ${FRONTEND_IMAGE}:${TAG} ${FRONTEND_IMAGE}:latest
              docker tag ${BACKEND_IMAGE}:${TAG}  ${BACKEND_IMAGE}:latest
              docker push ${FRONTEND_IMAGE}:latest
              docker push ${BACKEND_IMAGE}:latest
            """
          }
        }
      }
    }

    stage('Deploy to EC2 (main only)') {
      when { branch 'main' }
      steps {
        sshagent(credentials: ['ec2-ssh']) {
          sh """
            ssh -o StrictHostKeyChecking=no ${EC2_HOST} '
              set -e
              cd /srv/app
              # Ensure TAG/DOMAIN exist
              grep -q "^TAG=" .env.prod && sed -i "s/^TAG=.*/TAG=${TAG}/" .env.prod || echo "TAG=${TAG}" >> .env.prod
              # Pull & restart
              docker compose -f docker-compose.prod.yml --env-file .env.prod pull
              docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
              docker compose ps
            '
          """
        }
      }
    }
  }

  post {
    success { echo "Deployed ${TAG} to EC2" }
    failure { echo "Pipeline FAILED" }
  }
}

