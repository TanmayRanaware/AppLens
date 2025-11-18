pipeline {
  agent any

  options {
    timestamps()
    ansiColor('xterm')
    buildDiscarder(logRotator(numToKeepStr: '20'))
    timeout(time: 60, unit: 'MINUTES')
  }

  environment {
    REGISTRY           = 'docker.io'
    FRONTEND_IMAGE     = 'tanmayranaware/applens-frontend'
    BACKEND_IMAGE      = 'tanmayranaware/applens-backend'
    EC2_HOST           = 'ubuntu@ec2-3-21-127-72.us-east-2.compute.amazonaws.com'
    TAG                = "${env.BRANCH_NAME ?: 'main'}-${env.BUILD_NUMBER}"

    // Buildx / BuildKit
    DOCKER_BUILDKIT         = '1'
    DOCKER_CLI_EXPERIMENTAL = 'enabled'
    PLATFORMS               = 'linux/amd64,linux/arm64'
    FRONTEND_PLATFORMS      = 'linux/amd64'
    BACKEND_PLATFORMS       = "${PLATFORMS}"

    // Next.js build args
    NEXT_IGNORE_LINT   = '1'
    NEXT_IGNORE_TSC    = '1'
    NODE_OPTIONS_BUILD = '--max-old-space-size=2048'

    // Cap worker threads to reduce RAM spikes
    NEXT_CPU_COUNT     = '1'
    SWC_NODE_THREADS   = '1'
    RAYON_NUM_THREADS  = '1'

    // Push via output=… (compression removed as it's not supported in this buildx version)
    OUTPUT_OPTS = 'type=image,push=true'
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

          # Recreate a tuned builder (lowest concurrency + HTTP/1.1)
          docker buildx rm ci-builder || true
          docker buildx create \
            --name ci-builder \
            --driver docker-container \
            --driver-opt env.BUILDKIT_MAX_PARALLELISM=1 \
            --driver-opt env.BUILDKIT_LIMITED_SCOPE=1 \
            --driver-opt env.GODEBUG=http2client=0 \
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

            docker buildx use ci-builder
            docker buildx inspect --bootstrap

            # Simple retry wrapper (for single-arch frontend)
            retry_build_push() {
              local image="$1" tag="$2" dockerfile="$3" context="$4" platforms="$5"
              local attempts=4 delay=10 rc=0
              for ((i=1; i<=attempts; i++)); do
                echo "Attempt $i/$attempts: ${image}:${tag} (platforms=${platforms})"
                set +e
                docker buildx build \
                  --platform "${platforms}" \
                  --build-arg NEXT_IGNORE_LINT="${NEXT_IGNORE_LINT}" \
                  --build-arg NEXT_IGNORE_TSC="${NEXT_IGNORE_TSC}" \
                  --build-arg NODE_OPTIONS="${NODE_OPTIONS_BUILD}" \
                  --build-arg NEXT_CPU_COUNT="${NEXT_CPU_COUNT}" \
                  --build-arg SWC_NODE_THREADS="${SWC_NODE_THREADS}" \
                  --build-arg RAYON_NUM_THREADS="${RAYON_NUM_THREADS}" \
                  -t "${image}:${tag}" \
                  -t "${image}:latest" \
                  -f "${dockerfile}" "${context}" \
                  --output="${OUTPUT_OPTS}" \
                  --provenance=false \
                  --sbom=false \
                  --progress=plain
                rc=$?; set -e
                if [ $rc -eq 0 ]; then
                  echo "✅ Pushed ${image}:${tag}"
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

            retry_push_arch() {
              local image="$1" tag="$2" platform="$3" dockerfile="$4" context="$5"
              local attempts=4 delay=15 rc=0
              for ((i=1; i<=attempts; i++)); do
                echo "Attempt $i/$attempts: pushing ${image}:${tag} (platform=${platform})"
                set +e
                docker buildx build \
                  --platform "${platform}" \
                  -t "${image}:${tag}" \
                  -f "${dockerfile}" "${context}" \
                  --output="${OUTPUT_OPTS}" \
                  --provenance=false --sbom=false --progress=plain
                rc=$?; set -e
                if [ $rc -eq 0 ]; then
                  echo "✅ Successfully pushed ${image}:${tag}"
                  return 0
                fi
                if [ $i -lt $attempts ]; then
                  echo "⚠️ Push failed (rc=$rc). Retrying in ${delay}s..."
                  sleep "$delay"
                  delay=$(( delay*2 > 120 ? 120 : delay*2 ))
                fi
              done
              echo "❌ Failed to push ${image}:${tag} after ${attempts} attempts"
              return 1
            }

            # Per-arch serialized push + manifest (ALWAYS for backend)
            per_arch_then_manifest() {
              local image="$1" tag="$2" dockerfile="$3" context="$4"
              echo "Serializing per-arch pushes for ${image}:${tag} ..."
              # amd64
              if ! retry_push_arch "${image}" "${tag}-amd64" "linux/amd64" "${dockerfile}" "${context}"; then
                return 1
              fi

              # arm64
              if ! retry_push_arch "${image}" "${tag}-arm64" "linux/arm64" "${dockerfile}" "${context}"; then
                return 1
              fi

              echo "==> Creating multi-arch manifest ${image}:${tag} (+latest)"
              docker buildx imagetools create \
                -t "${image}:${tag}" \
                -t "${image}:latest" \
                "${image}:${tag}-amd64" \
                "${image}:${tag}-arm64"

              echo "✅ Multi-arch manifest created for ${image}:${tag}"
            }

            echo "Building & pushing FRONTEND (platforms: ${FRONTEND_PLATFORMS})..."
            retry_build_push "${FRONTEND_IMAGE}" "${TAG}" "frontend/Dockerfile" "frontend" "${FRONTEND_PLATFORMS}"

            echo "Building & pushing BACKEND (serialized per-arch) ..."
            per_arch_then_manifest "${BACKEND_IMAGE}" "${TAG}" "backend/Dockerfile" "backend"
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
                echo "${DOCKERHUB_PASS}" | docker login -u "${DOCKERHUB_USER}" --password-stdin ${REGISTRY} || true
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
  }

  post {
    success { echo "Deployed ${TAG} to EC2" }
    failure { echo "Pipeline FAILED" }
  }
}
