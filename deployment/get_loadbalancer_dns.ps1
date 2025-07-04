# Get Load Balancer DNS Name for Domain Configuration
# PowerShell script to retrieve the AWS Load Balancer DNS name for api.trod.ai

Write-Host "🔍 Getting Load Balancer DNS name for api.trod.ai configuration..." -ForegroundColor Blue
Write-Host ""

# Check if AWS CLI is available
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Host "❌ AWS CLI not found. Please install AWS CLI first." -ForegroundColor Red
    Write-Host "   Download from: https://aws.amazon.com/cli/" -ForegroundColor Yellow
    exit 1
}

# Check AWS configuration
try {
    $null = aws sts get-caller-identity 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI not configured"
    }
} catch {
    Write-Host "❌ AWS CLI not configured. Please run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Get the load balancer DNS name from CloudFormation
$StackName = "video-clip-generator-production-infrastructure"
try {
    $DnsName = aws cloudformation describe-stacks --stack-name $StackName --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNSName'].OutputValue" --output text
    
    if ([string]::IsNullOrEmpty($DnsName) -or $DnsName -eq "None") {
        throw "DNS name not found"
    }
} catch {
    Write-Host "❌ Could not retrieve Load Balancer DNS name." -ForegroundColor Red
    Write-Host "   Make sure the infrastructure stack is deployed successfully." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "🔧 Troubleshooting:" -ForegroundColor Cyan
    Write-Host "   1. Check if the stack exists:"
    Write-Host "      aws cloudformation describe-stacks --stack-name $StackName"
    Write-Host ""
    Write-Host "   2. Check deployment status:"
    Write-Host "      aws cloudformation describe-stack-events --stack-name $StackName"
    exit 1
}

Write-Host "✅ Load Balancer DNS Name: $DnsName" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps for Domain Configuration:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. 🌐 Configure DNS Records:" -ForegroundColor Yellow
Write-Host "   In your domain management panel for trod.ai, create:"
Write-Host ""
Write-Host "   Option A - CNAME Record (Recommended):" -ForegroundColor White
Write-Host "   Type: CNAME"
Write-Host "   Name: api"
Write-Host "   Value: $DnsName"
Write-Host "   TTL: 300"
Write-Host ""
Write-Host "   Option B - A Record (Alternative):" -ForegroundColor White
Write-Host "   Type: A"
Write-Host "   Name: api"
Write-Host "   Value: [Get IP of $DnsName]"
Write-Host "   TTL: 300"
Write-Host ""
Write-Host "2. 🔒 Configure SSL:" -ForegroundColor Yellow
Write-Host "   - Ensure your SSL certificate covers api.trod.ai"
Write-Host "   - Point SSL origin to: $DnsName"
Write-Host "   - Set SSL mode to 'Full' or 'Full (Strict)'"
Write-Host ""
Write-Host "3. 🧪 Test Configuration (after DNS propagation ~5-15 minutes):" -ForegroundColor Yellow
Write-Host "   curl https://api.trod.ai/api/health"
Write-Host "   curl https://api.trod.ai/docs"
Write-Host ""
Write-Host "4. 📖 For detailed instructions, see: deployment/DOMAIN_SETUP.md" -ForegroundColor Yellow
Write-Host ""

# Also get the regular load balancer URL for reference
try {
    $LbUrl = aws cloudformation describe-stacks --stack-name $StackName --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerUrl'].OutputValue" --output text
    
    if (-not [string]::IsNullOrEmpty($LbUrl) -and $LbUrl -ne "None") {
        Write-Host "📝 Current Load Balancer URL (for testing): $LbUrl" -ForegroundColor Gray
        Write-Host ""
    }
} catch {
    # Ignore if not available
}

Write-Host "🎯 Your API will be available at: https://api.trod.ai" -ForegroundColor Green 