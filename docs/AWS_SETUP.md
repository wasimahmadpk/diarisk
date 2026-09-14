# Deploying DiaRisk to AWS App Runner

The API runs as a container on [AWS App Runner](https://aws.amazon.com/apprunner/):
you hand it an image, it gives you an HTTPS endpoint and scales it. No VPC,
load balancer or cluster to manage.

```
docker image ──push──> ECR ──pull──> App Runner ──> https://<id>.<region>.awsapprunner.com
```

Everything is described in `terraform-aws/`.

## 1. Tools

```bash
brew install awscli
brew tap hashicorp/tap && brew install hashicorp/tap/terraform
aws --version
terraform -version
```

## 2. AWS account

Create an account at https://aws.amazon.com, then an IAM user with
programmatic access (or use IAM Identity Center) and configure the CLI:

```bash
aws configure
# Access key, secret, region: eu-central-1, output: json
aws sts get-caller-identity   # should print your account id
```

Free tier note: App Runner is **not** free. See [costs](#costs) below.

## 3. Create the ECR repository first

App Runner refuses to start if the image does not exist yet, so create the
registry before the service:

```bash
cd terraform-aws
cp terraform.tfvars.example terraform.tfvars   # adjust if you like
terraform init
terraform apply -target=aws_ecr_repository.diarisk
```

## 4. Build and push the image

App Runner runs on x86_64, so on an Apple Silicon Mac you must build for
`linux/amd64`:

```bash
cd ..
AWS_REGION=eu-central-1
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGISTRY=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $REGISTRY

docker build --platform linux/amd64 -t $REGISTRY/diarisk:latest .
docker push $REGISTRY/diarisk:latest
```

## 5. Create the service

```bash
cd terraform-aws
terraform apply
```

This creates the App Runner service, its autoscaling configuration, the IAM
role App Runner uses to pull from ECR, and the role GitHub Actions assumes
later. Takes a few minutes.

```bash
terraform output service_url
```

Check it:

```bash
URL=$(terraform output -raw service_url)
curl -s $URL/health
curl -s $URL/predict -H 'Content-Type: application/json' -d @../samples/example_patient.json
open $URL/docs
```

## 6. Automatic deploys from GitHub Actions

The `deploy` job in `.github/workflows/ci.yml` builds the image, pushes it to
ECR and waits for the rollout. It authenticates via OIDC — no access keys in
GitHub.

```bash
terraform output github_actions_role_arn
terraform output service_arn
```

Then, in the repository settings:

| kind     | name                    | value                             |
|----------|-------------------------|-----------------------------------|
| secret   | `AWS_DEPLOY_ROLE_ARN`   | `github_actions_role_arn` output  |
| variable | `AWS_REGION`            | `eu-central-1`                    |
| variable | `ECR_REPOSITORY`        | `diarisk`                         |
| variable | `APPRUNNER_SERVICE_ARN` | `service_arn` output              |
| variable | `AWS_DEPLOY`            | `true`                            |

Or from the CLI:

```bash
gh secret set AWS_DEPLOY_ROLE_ARN --body "$(terraform output -raw github_actions_role_arn)"
gh variable set AWS_REGION --body "eu-central-1"
gh variable set ECR_REPOSITORY --body "diarisk"
gh variable set APPRUNNER_SERVICE_ARN --body "$(terraform output -raw service_arn)"
gh variable set AWS_DEPLOY --body "true"
```

Without `AWS_DEPLOY=true` the deploy job is skipped, so the pipeline keeps
working for anyone without AWS access.

Because the service has `auto_deployments_enabled`, a new `:latest` in ECR is
picked up by App Runner on its own; the workflow only waits and pings
`/health`.

## Configuration

Defaults live in `terraform-aws/variables.tf`:

| variable          | default | meaning                                   |
|-------------------|---------|-------------------------------------------|
| `cpu` / `memory`  | 1 vCPU / 2 GB | per instance                        |
| `min_size`        | 1       | App Runner cannot scale to zero           |
| `max_size`        | 3       | upper scaling limit                       |
| `max_concurrency` | 80      | requests per instance before scaling out  |

## Costs

Unlike Cloud Run, App Runner keeps at least one instance warm and bills
memory continuously (~$0.007/GB-h, i.e. roughly $10/month for 2 GB idle);
vCPU is only billed while requests are processed.

Pause the service when you are not using it:

```bash
aws apprunner pause-service --service-arn $(terraform output -raw service_arn)
aws apprunner resume-service --service-arn $(terraform output -raw service_arn)
```

Or remove everything:

```bash
terraform destroy
```

## Troubleshooting

- **Service stuck in `CREATE_FAILED`** — usually the image is missing or built
  for arm64. Rebuild with `--platform linux/amd64` and push again.
- **Health check failing** — App Runner probes `/health` on port 8000; check
  the application logs in CloudWatch under `/aws/apprunner/diarisk-api`.
- **OIDC provider already exists** — set `create_github_oidc_provider = false`
  in `terraform.tfvars`; the config then looks the existing one up.
