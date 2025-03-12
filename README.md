# Paper-Reviewer-AWS

A web application for managing and reviewing academic papers, deployed on AWS.

## Description

Paper-Reviewer-AWS is a platform that facilitates the academic paper review process. It allows users to submit papers, assign reviewers, and manage the review workflow in a streamlined manner.

## Features

- User authentication and authorization
- Paper submission and management
- Reviewer assignment
- Review submission and tracking
- Status tracking for papers
- Secure file storage

## Prerequisites

- AWS Account
- Node.js (v14 or higher)
- npm or yarn
- AWS CLI configured locally

## AWS Services Used

- AWS Lambda
- Amazon S3 (for paper storage)
- Amazon DynamoDB (for data persistence)
- Amazon Cognito (for authentication)
- API Gateway
- AWS CloudFormation

## Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Paper-Reviewer-AWS.git
cd Paper-Reviewer-AWS
```

2. Install dependencies:
```bash
npm install
```

3. Configure AWS credentials:
```bash
aws configure
```

4. Create a `.env` file with necessary environment variables:
```bash
AWS_REGION=your-region
COGNITO_USER_POOL_ID=your-user-pool-id
COGNITO_CLIENT_ID=your-client-id
```

## Deployment

1. Create an S3 bucket for CloudFormation artifacts (only needed once):
```bash
aws s3 mb s3://paper-reviewer-artifacts-<your-unique-suffix>
```

2. Package the CloudFormation template:
```bash
aws cloudformation package \
    --template-file template.yaml \
    --s3-bucket paper-reviewer-artifacts-<your-unique-suffix> \
    --output-template-file packaged.yaml
```

3. Deploy the CloudFormation stack:
```bash
aws cloudformation deploy \
    --template-file packaged.yaml \
    --stack-name paper-reviewer-stack \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        Environment=dev \
        CognitoUserPoolName=PaperReviewerUserPool
```

4. Get the stack outputs (API endpoint, Cognito details, etc.):
```bash
aws cloudformation describe-stacks \
    --stack-name paper-reviewer-stack \
    --query 'Stacks[0].Outputs' \
    --output table
```

5. Update your `.env` file with the stack outputs:
```bash
API_ENDPOINT=<API Gateway URL from stack output>
COGNITO_USER_POOL_ID=<User Pool ID from stack output>
COGNITO_CLIENT_ID=<Client ID from stack output>
```

Note: Make sure your AWS CLI is configured with appropriate permissions to create and manage CloudFormation stacks, IAM roles, and other AWS services.

To delete the stack when needed:
```bash
aws cloudformation delete-stack --stack-name paper-reviewer-stack
```

## Project Structure

```
Paper-Reviewer-AWS/
├── src/
│   ├── handlers/         # Lambda function handlers
│   ├── models/          # Data models
│   └── utils/           # Utility functions
├── tests/               # Test files
├── template.yaml        # AWS SAM template
└── package.json
```

## API Endpoints

- POST /papers - Submit a new paper
- GET /papers - List all papers
- GET /papers/{id} - Get paper details
- POST /reviews - Submit a review
- GET /reviews/{paperId} - Get reviews for a paper

## Security

- All endpoints are protected with AWS Cognito authentication
- File uploads are secured using presigned URLs
- Role-based access control for different user types

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository.