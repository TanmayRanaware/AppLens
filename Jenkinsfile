pipeline {
  agent any

  options {
    timestamps()
    ansiColor('xterm')
    buildDiscarder(logRotator(numToKeepStr: '20'))
    timeout(time: 60, unit: 'MINUTES')
  }

  environment {
    REGISTRY                = 'docker.io'
    FRONTEND_IMAGE          = 'tanmayranaware/applens-frontend'
    BACKEND_IMAGE           = 'tanmayranaware/applens-backend'
    EC2_HOST                = 'ubuntu@ec2-3-21-127-72.us-east-2.compute.amazonaws.com'

    TAG                     = "${env.BRANCH_NAME ?: 'main'}-${env.BUILD_NUMBER}"

    // Buildx / BuildKit
    DOCKER_BUILDKIT         = '1'
    DOCKER_CLI_EXPERIMENTAL = 'enabled'
    PLATFORMS               = 'linux/amd64,linux/arm64'      // default multi-arch
    FRONTEND_PLATFORMS      = 'linux/amd64'                  // 👈 force single-arch for frontend
    BACKEND_PLATFORMS       = "${PLATFORMS}"                 // keep backend multi-arch

    // Next.js build args (Dockerfile uses them)
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
          docker info | sed -n '1,80p' || true
        '''
      }
    }

    stage('Enable Buildx') {
      steps {
        sh '''
          set -euxo pipefail

          docker context use default || true

          # Recreate a tuned builder to reduce parallelism (helps memory)
          docker buildx rm ci-builder || true
          docker buildx create \
            --name ci-builder \
            --driver docker-container \
            --driver-opt env.BUILDKIT_MAX_PARALLELISM=2 \
            --use

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

            echo "$DOCKERHUB_PASS" | docker login -u "$DOCKERHUB_USER" --password-stdin "$REGISTRY"

            # ensure the tuned builder is active
            docker buildx use ci-builder
            docker buildx inspect --bootstrap

            retry_build_push() {
              local image="$1" tag="$2" dockerfile="$3" context="$4" platforms="$5"
              local attempts=5 delay=8 rc=0

              for ((i=1; i<=attempts; i++)); do
                echo "Attempt $i/$attempts: building & pushing ${image}:${tag} (platforms=${platforms})"
                set +e
                docker buildx build \
                  --platform "${platforms}" \
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
                  delay=$(( delay*2 > 60 ? 60 : delay*2 ))
                fi
              done

              echo "❌ Failed to push ${image}:${tag} after ${attempts} attempts"
              return 1
            }

            echo "Building and pushing FRONTEND (platforms: ${FRONTEND_PLATFORMS})..."
            retry_build_push "${FRONTEND_IMAGE}" "${TAG}" "frontend/Dockerfile" "frontend" "${FRONTEND_PLATFORMS}"

            echo "Building and pushing BACKEND (platforms: ${BACKEND_PLATFORMS})..."
            retry_build_push "${BACKEND_IMAGE}" "${TAG}" "backend/Dockerfile" "backend" "${BACKEND_PLATFORMS}"
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

                # Login on the host (compose will pull)
                echo "${DOCKERHUB_PASS}" | docker login -u "${DOCKERHUB_USER}" --password-stdin ${REGISTRY} || true

                cd /srv/app

                # Persist the image tag for compose
                if grep -q "^TAG=" .env.prod; then
                  sed -i "s/^TAG=.*/TAG=${TAG}/" .env.prod
                else
                  echo "TAG=${TAG}" >> .env.prod
                fi

                # Pull + recreate with the new tag
                docker compose -f docker-compose.prod.yml --env-file .env.prod pull
                docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

                docker compose -f docker-compose.prod.yml --env-file .env.prod ps
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
