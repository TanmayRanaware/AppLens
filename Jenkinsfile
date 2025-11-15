pipeline {
  agent any

  options {
    timestamps()
    ansiColor('xterm')
    buildDiscarder(logRotator(numToKeepStr: '20'))
    // Global safety timeout (can be overridden per-stage)
    timeout(time: 60, unit: 'MINUTES')
  }

  environment {
    REGISTRY                = 'docker.io'
    FRONTEND_IMAGE          = 'tanmayranaware/applens-frontend'
    BACKEND_IMAGE           = 'tanmayranaware/applens-backend'
    EC2_HOST                = 'ubuntu@ec2-3-21-127-72.us-east-2.compute.amazonaws.com'
    TAG                     = "${env.BRANCH_NAME ?: 'main'}-${env.BUILD_NUMBER}"
    DOCKER_BUILDKIT         = '1'
    DOCKER_CLI_EXPERIMENTAL = 'enabled'
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Check Docker env') {
      steps {
        sh '''
          set -euxo pipefail
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
          set -euxo pipefail
          docker context use default || true
          docker buildx create --use || true
          docker buildx inspect --bootstrap
        '''
      }
    }

    stage('Build & Push Images (amd64)') {
      options {
        // Keep this tighter so pushes don't hang forever
        timeout(time: 40, unit: 'MINUTES')
      }
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                          usernameVariable: 'DOCKERHUB_USER',
                                          passwordVariable: 'DOCKERHUB_PASS')]) {
          sh '''
            set -euxo pipefail

            # Login (registry optional here since it's docker.io)
            echo "$DOCKERHUB_PASS" | docker login -u "$DOCKERHUB_USER" --password-stdin "$REGISTRY"

            # Ensure buildx builder is ready
            docker buildx create --use || true
            docker buildx inspect --bootstrap

            # Retryable build+push helper
            retry_build_push() {
              local image="$1" tag="$2" dockerfile="$3" context="$4"
              local attempts=5 delay=8 rc=0

              for ((i=1; i<=attempts; i++)); do
                echo "Attempt $i/$attempts: building & pushing ${image}:${tag}"
                set +e
                docker buildx build \
                  --platform linux/amd64 \
                  -t "${image}:${tag}" \
                  -t "${image}:latest" \
                  -f "${dockerfile}" "${context}" \
                  --push \
                  --provenance=false \
                  --sbom=false \
                  --progress=plain
                rc=$?
                set -e

                if [ $rc -eq 0 ]; then
                  echo "✅ Successfully pushed ${image}:${tag}"
                  return 0
                fi

                if [ $i -lt $attempts ]; then
                  echo "⚠️ Push failed (rc=$rc). Retrying in ${delay}s..."
                  sleep "$delay"
                  # Exponential backoff with cap
                  delay=$(( delay*2 > 60 ? 60 : delay*2 ))
                fi
              done

              echo "❌ Failed to push ${image}:${tag} after ${attempts} attempts"
              return 1
            }

            echo "Building and pushing frontend image..."
            retry_build_push "${FRONTEND_IMAGE}" "${TAG}" "frontend/Dockerfile" "frontend"

            echo "Building and pushing backend image..."
            retry_build_push "${BACKEND_IMAGE}" "${TAG}" "backend/Dockerfile" "backend"
          '''
        }
      }
    }

    // Always deploy after build & push
    stage('Deploy to EC2') {
      options {
        timeout(time: 20, unit: 'MINUTES')
      }
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                          usernameVariable: 'DOCKERHUB_USER',
                                          passwordVariable: 'DOCKERHUB_PASS')]) {
          sshagent(credentials: ['ec2-ssh']) {
            sh """
              set -euxo pipefail
              ssh -o StrictHostKeyChecking=no ${EC2_HOST} '
                set -euxo pipefail

                # Login to Docker Hub on EC2
                echo '${DOCKERHUB_PASS}' | docker login -u '${DOCKERHUB_USER}' --password-stdin docker.io || true

                cd /srv/app

                # Persist the tag used by docker-compose
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
