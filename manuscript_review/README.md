# Paper Reviewer Application

## Security Setup

1. Create a `.env` file based on `.env.example`
2. Never commit the `.env` file or any files containing credentials
3. Use AWS Secrets Manager or Parameter Store for production credentials
4. Rotate AWS access keys regularly
5. Use IAM roles with minimal required permissions

## Local Development Setup

1. Copy `.env.example` to `.env`
2. Fill in your development credentials
3. Never use production credentials in development
4. Use local S3 alternatives for development when possible

## Production Deployment

1. Use environment variables for all sensitive information
2. Never hardcode credentials in any files
3. Use AWS Parameter Store or Secrets Manager
4. Enable CloudTrail logging
5. Monitor for unauthorized access

## Security Best Practices

1. Keep all dependencies updated
2. Use HTTPS everywhere
3. Implement proper CORS policies
4. Use secure cookies
5. Implement rate limiting
6. Monitor AWS CloudWatch logs
7. Regular security audits 