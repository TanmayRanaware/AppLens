pipeline {
  agent any

  options { timestamps(); ansiColor('xterm'); buildDiscarder(logRotator(numToKeepStr: '20')) }

  environment {
    REGISTRY       = 'docker.io'
    FRONTEND_IMAGE = 'tanmayranaware/applens-frontend'
    BACKEND_IMAGE  = 'tanmayranaware/applens-backend'
    EC2_HOST       = 'ubuntu@ec2-3-21-127-72.us-east-2.compute.amazonaws.com'
    TAG            = "${env.BRANCH_NAME ?: 'main'}-${env.BUILD_NUMBER}"
    DOCKER_BUILDKIT = '1'
    DOCKER_CLI_EXPERIMENTAL = 'enabled'
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
          docker info | sed -n '1,40p' || true
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
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                          usernameVariable: 'DOCKERHUB_USER',
                                          passwordVariable: 'DOCKERHUB_PASS')]) {
          sh '''
            set -eux
            echo "$DOCKERHUB_PASS" | docker login -u "$DOCKERHUB_USER" --password-stdin docker.io

            # ensure buildx builder is ready
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

    // Always deploy after build & push
    stage('Deploy to EC2') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                          usernameVariable: 'DOCKERHUB_USER',
                                          passwordVariable: 'DOCKERHUB_PASS')]) {
          sshagent(credentials: ['ec2-ssh']) {
            sh """
              set -eux
              ssh -o StrictHostKeyChecking=no ${EC2_HOST} '
                set -eux

                # Login to Docker Hub on EC2 (Jenkins substitutes the secrets here; Jenkins will mask them in logs)
                echo '${DOCKERHUB_PASS}' | docker login -u '${DOCKERHUB_USER}' --password-stdin docker.io || true

                cd /srv/app

                # Persist the tag used by docker-compose (if your compose references it)
                if grep -q "^TAG=" .env.prod; then
                  sed -i "s/^TAG=.*/TAG=${TAG}/" .env.prod
                else
                  echo "TAG=${TAG}" >> .env.prod
                fi

                # Pull and restart with the fresh images
                docker compose -f docker-compose.prod.yml --env-file .env.prod pull
                docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
                docker compose -f docker-compose.prod.yml --env-file .env.prod ps

                # Optional cleanup
                docker image prune -f || true
              '
            """
          }
        }
      }
    }
  }

  post {
    success { echo "Deployed ${TAG} to EC2" }
    failure { echo "Pipeline FAILED" }
  }
}
