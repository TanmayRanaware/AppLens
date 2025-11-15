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

            # Function to retry buildx build with push
            retry_build_push() {
              local image=$1
              local tag=$2
              local dockerfile=$3
              local context=$4
              local max_attempts=3
              local attempt=1
              local delay=5
              
              while [ $attempt -le $max_attempts ]; do
                echo "Attempt $attempt/$max_attempts: Building and pushing ${image}:${tag}"
                if docker buildx build --platform linux/amd64 \
                  -t ${image}:${tag} -t ${image}:latest \
                  -f ${dockerfile} ${context} --push; then
                  echo "Successfully built and pushed ${image}:${tag}"
                  return 0
                else
                  if [ $attempt -lt $max_attempts ]; then
                    echo "Build/push failed, retrying in ${delay}s..."
                    sleep $delay
                    delay=$((delay * 2))  # Exponential backoff: 5s, 10s, 20s
                  fi
                  attempt=$((attempt + 1))
                fi
              done
              echo "Failed to build/push ${image}:${tag} after $max_attempts attempts"
              return 1
            }

            # Build and push with retry logic
            echo "Building and pushing frontend image..."
            retry_build_push ${FRONTEND_IMAGE} ${TAG} frontend/Dockerfile frontend

            echo "Building and pushing backend image..."
            retry_build_push ${BACKEND_IMAGE} ${TAG} backend/Dockerfile backend
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
