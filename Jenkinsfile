pipeline {
  agent any

  options {
    timestamps()
    ansiColor('xterm')
    buildDiscarder(logRotator(numToKeepStr: '20'))
    timeout(time: 60, unit: 'MINUTES') // global safety timeout
  }

  environment {
    REGISTRY                = 'docker.io'
    FRONTEND_IMAGE          = 'tanmayranaware/applens-frontend'
    BACKEND_IMAGE           = 'tanmayranaware/applens-backend'
    EC2_HOST                = 'ubuntu@ec2-3-21-127-72.us-east-2.compute.amazonaws.com'
    TAG                     = "${env.BRANCH_NAME ?: 'main'}-${env.BUILD_NUMBER}"
    DOCKER_BUILDKIT         = '1'
    DOCKER_CLI_EXPERIMENTAL = 'enabled'

    // Build args consumed by your Dockerfile (see notes below)
    NEXT_IGNORE_LINT        = '1'
    NEXT_IGNORE_TSC         = '1'
    NODE_OPTIONS_BUILD      = '--max-old-space-size=2048'
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
          docker info | sed -n '1,60p' || true
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

    stage('Build & Push Images') {
      options { timeout(time: 40, unit: 'MINUTES') }
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                          usernameVariable: 'DOCKERHUB_USER',
                                          passwordVariable: 'DOCKERHUB_PASS')]) {
          sh '''
            set -euxo pipefail

            # Login (registry optional for docker.io)
            echo "$DOCKERHUB_PASS" | docker login -u "$DOCKERHUB_USER" --password-stdin "$REGISTRY"

            # Ensure buildx builder is ready
            docker buildx create --use || true
            docker buildx inspect --bootstrap

            # Auto-select platform to avoid QEMU when running on Apple Silicon agents
            # arm64 host -> build linux/arm64; otherwise linux/amd64
            if uname -m | grep -qi 'arm\\|aarch64'; then
              export TARGET_PLATFORM=linux/arm64
            else
              export TARGET_PLATFORM=linux/amd64
            fi
            echo "Using buildx --platform=${TARGET_PLATFORM}"

            retry_build_push() {
              local image="$1" tag="$2" dockerfile="$3" context="$4"
              local attempts=5 delay=8 rc=0

              for ((i=1; i<=attempts; i++)); do
                echo "Attempt $i/$attempts: building & pushing ${image}:${tag}"
                set +e
                docker buildx build \
                  --platform "${TARGET_PLATFORM}" \
                  --build-arg NEXT_IGNORE_LINT="${NEXT_IGNORE_LINT}" \
                  --build-arg NEXT_IGNORE_TSC="${NEXT_IGNORE_TSC}" \
                  --build-arg NODE_OPTIONS="${NODE_OPTIONS_BUILD}" \
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

    stage('Deploy to EC2') {
      options { timeout(time: 20, unit: 'MINUTES') }
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
