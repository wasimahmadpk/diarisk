# Deploying DiaRisk to AWS Lambda

The API runs as a container on AWS Lambda behind a
[Function URL](https://docs.aws.amazon.com/lambda/latest/dg/lambda-urls.html).
Lambda scales to zero: when nobody calls the API, nothing runs and nothing is
billed.

```
docker image ──push──> ECR ──> Lambda (container) ──> https://<id>.lambda-url.<region>.on.aws
```

`src/lambda_handler.py` wraps the same FastAPI app with
[Mangum](https://github.com/Kludex/mangum), so local `uvicorn` and Lambda serve
identical code. Infrastructure lives in `terraform-aws/`.

## 1. Tools

```bash
brew install awscli
brew tap hashicorp/tap && brew install hashicorp/tap/terraform
aws --version
terraform -version
```

## 2. AWS credentials

```bash
aws configure
# Access key, secret, region: eu-central-1, output: json
aws sts get-caller-identity   # should print your account id
```

## 3. Create the ECR repository first

Lambda cannot be created before its image exists, so build the registry first:

```bash
cd terraform-aws
cp terraform.tfvars.example terraform.tfvars
# optional but recommended: set budget_alert_email
terraform init
terraform apply -target=aws_ecr_repository.diarisk
```

## 4. Build and push the image

Lambda runs on x86_64, so on an Apple Silicon Mac build for `linux/amd64`:

```bash
cd ..
AWS_REGION=eu-central-1
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGISTRY=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $REGISTRY

docker build --platform linux/amd64 -f Dockerfile.lambda -t $REGISTRY/diarisk:latest .
docker push $REGISTRY/diarisk:latest
```

## 5. Create the function

```bash
cd terraform-aws
terraform apply
```

This creates the Lambda function, its Function URL, the execution role, a log
group with 7-day retention and the role GitHub Actions uses to deploy.

```bash
URL=$(terraform output -raw function_url)
curl -s ${URL%/}/health
curl -s ${URL%/}/predict -H 'Content-Type: application/json' -d @../samples/example_patient.json
open ${URL%/}/docs
```

The first call after a while is a cold start and takes a few seconds (the
image has to be loaded and the model unpickled); afterwards responses are fast
while the function stays warm.

## 6. Automatic deploys from GitHub Actions

The `deploy` job in `.github/workflows/ci.yml` builds `Dockerfile.lambda`,
pushes it to ECR and points the function at the new image. It authenticates
via OIDC — no AWS keys stored in GitHub.

```bash
gh secret set AWS_DEPLOY_ROLE_ARN --body "$(terraform output -raw github_actions_role_arn)"
gh variable set AWS_REGION --body "eu-central-1"
gh variable set ECR_REPOSITORY --body "diarisk"
gh variable set LAMBDA_FUNCTION_NAME --body "$(terraform output -raw function_name)"
gh variable set AWS_DEPLOY --body "true"
```

Without `AWS_DEPLOY=true` the deploy job is skipped, so the pipeline keeps
working for anyone without AWS access.

Terraform ignores changes to `image_uri`, so a later `terraform apply` will not
roll back what CI deployed.

## Costs

| resource | free tier | after that |
|----------|-----------|------------|
| Lambda requests | 1M / month, permanent | $0.20 per 1M |
| Lambda compute | 400,000 GB-s / month, permanent | $0.0000166667 per GB-s |
| Function URL | included | – |
| CloudWatch Logs | 5 GB ingest / month | $0.50 per GB |
| ECR storage | 500 MB / month for 12 months | $0.10 per GB-month |

At 1024 MB a request of ~1 s uses 1 GB-s, so the free tier covers roughly
400,000 calls per month. Idle cost is zero.

The only thing that can eventually cost a little is ECR storage. The image is
roughly 400 MB compressed, which still fits the free 500 MB; layers are shared
between tags, so keeping the last 3 images (lifecycle policy) barely adds to
that. After the 12-month window expect a few cents per month.

Guardrails already in the config:

- `reserved_concurrency = 5` caps parallel executions, so even a traffic flood
  cannot run up a large bill.
- `log_retention_days = 7` stops logs from piling up.
- `budget_alert_email` sends a mail as soon as the forecast exceeds $1/month.

Remove everything:

```bash
terraform destroy
```

## Troubleshooting

- **`Runtime.InvalidEntrypoint` / image errors** — the image was built for
  arm64. Rebuild with `--platform linux/amd64`.
- **`FileNotFoundError` for the model** — `models/diarisk_lightgbm.joblib` must
  exist before the build; run `python src/train_lightgbm.py`.
- **Timeouts on the first call** — cold start; raise `timeout_seconds` or call
  `/health` once to warm the function.
- **Logs** — `aws logs tail /aws/lambda/diarisk-api --follow`.
- **OIDC provider already exists** — set `create_github_oidc_provider = false`
  in `terraform.tfvars`.
