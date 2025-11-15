pipeline {
  agent any

  options { timestamps(); ansiColor('xterm'); buildDiscarder(logRotator(numToKeepStr: '20')) }

  environment {
    REGISTRY       = 'docker.io'
    FRONTEND_IMAGE = 'tanmayranaware/applens-frontend'
    BACKEND_IMAGE  = 'tanmayranaware/applens-backend'
    EC2_HOST       = 'ubuntu@ec2-3-21-127-72.us-east-2.compute.amazonaws.com'
    TAG            = "${env.BRANCH_NAME ?: 'main'}-${env.BUILD_NUMBER}"
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Check Docker env') {
      steps {
        sh '''
          set -eux
          docker version || true
          docker buildx version || true
          docker context ls || true
          docker info | sed -n '1,30p' || true
        '''
      }
    }

    stage('Enable Buildx (once per agent)') {
      steps {
        sh '''
          set -eux
          docker context use default || true
          docker buildx create --use || true
          docker buildx inspect --bootstrap
        '''
      }
    }

    stage('Build & Push Images (amd64)') {
      environment {
        DOCKER_CLI_EXPERIMENTAL = 'enabled'
        DOCKER_BUILDKIT = '1'
      }
      steps {
        withCredentials([string(credentialsId: 'dockerhub-creds', variable: 'DOCKERHUB_TOKEN')]) {
          sh '''
            set -eux
            echo "$DOCKERHUB_TOKEN" | docker login -u tanmayranaware --password-stdin docker.io

            docker buildx create --use || true
            docker buildx inspect --bootstrap

            docker buildx build --platform linux/amd64 \
              -t ${FRONTEND_IMAGE}:${TAG} -t ${FRONTEND_IMAGE}:latest \
              -f frontend/Dockerfile frontend --push

            docker buildx build --platform linux/amd64 \
              -t ${BACKEND_IMAGE}:${TAG} -t ${BACKEND_IMAGE}:latest \
              -f backend/Dockerfile backend --push
          '''
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
              if grep -q "^TAG=" .env.prod; then
                sed -i "s/^TAG=.*/TAG=${TAG}/" .env.prod
              else
                echo "TAG=${TAG}" >> .env.prod
              fi
              docker compose -f docker-compose.prod.yml --env-file .env.prod pull
              docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
              docker compose -f docker-compose.prod.yml --env-file .env.prod ps
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
