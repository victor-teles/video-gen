# 🚀 AWS Console Setup Guide for Editur AI Backend Deployment

## 📧 Your Account: azeemushanofficial@gmail.com

This guide will walk you through setting up your AWS account for the Editur AI backend deployment.

---

## 🎯 **Step 1: Complete AWS Account Setup**

### 1.1 Login to AWS Console
1. Go to https://aws.amazon.com/console/
2. Click "Sign In to the Console" 
3. Use: **azeemushanofficial@gmail.com**
4. Enter your password

### 1.2 Complete Account Verification
If you haven't already:
- ✅ Verify your email address
- ✅ Add a valid credit/debit card
- ✅ Verify your phone number
- ✅ Choose support plan (Basic - Free is fine)

---

## 🔐 **Step 2: Create IAM User for CLI Access**

### 2.1 Create IAM User (IMPORTANT - Don't use root credentials)

1. **Navigate to IAM Service:**
   - In AWS Console search bar, type "IAM"
   - Click "IAM" (Identity and Access Management)

2. **Create New User:**
   - Click "Users" in left sidebar
   - Click "Create user" button
   - **User name:** `editur-ai-admin`
   - **Access type:** Check "Programmatic access"
   - Click "Next: Permissions"

3. **Attach Policies:**
   For simplicity (you can restrict later), attach these policies:
   - ✅ `AmazonEC2FullAccess`
   - ✅ `AmazonS3FullAccess` 
   - ✅ `IAMFullAccess`
   - ✅ `AmazonVPCFullAccess`
   - ✅ `CloudWatchFullAccess`
   
   Click "Next: Tags" → "Next: Review" → "Create user"

4. **SAVE THESE CREDENTIALS (IMPORTANT!):**
   ```
   Access Key ID: AKIA******************
   Secret Access Key: ****************************************
   ```
   ⚠️ **Download the CSV file - you can only see the secret once!**

---

## 🌍 **Step 3: Set Default Region**

### 3.1 Choose Your Region
- **Recommended:** `us-east-1` (N. Virginia)
- **Why:** Cheapest region, most services available
- **Alternative:** `us-west-2` (Oregon) if you prefer West Coast

### 3.2 Set Region in Console
- Look at top-right corner of AWS Console
- Click the region dropdown
- Select "US East (N. Virginia) us-east-1"

---

## 💰 **Step 4: Set Up Billing Alerts (CRITICAL)**

### 4.1 Enable Billing Alerts
1. **Go to Billing Dashboard:**
   - Click your account name (top-right) → "Billing and Cost Management"
   - OR search "Billing" in console

2. **Enable Cost Alerts:**
   - Left sidebar → "Billing preferences"
   - Check ✅ "Receive Billing Alerts"
   - Check ✅ "Receive Free Tier Usage Alerts"
   - Enter email: **azeemushanofficial@gmail.com**
   - Click "Save preferences"

### 4.2 Create Budget Alert
1. **Navigate to Budgets:**
   - Left sidebar → "Budgets"
   - Click "Create budget"

2. **Budget Configuration:**
   - **Budget type:** Cost budget
   - **Budget name:** `Editur-AI-Monthly-Budget`
   - **Budget amount:** `$25.00` (recommended starting point)
   - **Budget period:** Monthly
   - **Start month:** Current month

3. **Alert Settings:**
   - **Alert threshold:** 80% of budgeted amount ($20)
   - **Email recipients:** azeemushanofficial@gmail.com
   - Click "Create budget"

---

## 🔒 **Step 5: Security Setup**

### 5.1 Enable MFA (Multi-Factor Authentication)
1. **Go to Security Credentials:**
   - Click your account name → "Security Credentials"
   - OR go to IAM → Users → your root account

2. **Set up MFA:**
   - Click "Assign MFA device"
   - Choose "Virtual MFA device"
   - Use Google Authenticator or Authy app
   - Scan QR code and enter two consecutive codes

### 5.2 Create Key Pair for EC2
1. **Navigate to EC2:**
   - Search "EC2" in console → Click "EC2"

2. **Create Key Pair:**
   - Left sidebar → "Network & Security" → "Key Pairs"
   - Click "Create key pair"
   - **Name:** `editur-ai-key`
   - **Key pair type:** RSA
   - **Private key file format:** .pem (for macOS/Linux)
   - Click "Create key pair"
   - **SAVE the downloaded .pem file securely!**

---

## 🎯 **Step 6: Pre-deployment Verification**

### 6.1 Check Service Limits
1. **EC2 Limits:**
   - EC2 Dashboard → "Limits" (left sidebar)
   - Verify you can launch at least 1 t3.medium instance
   - Default limit is usually 5-20 instances

### 6.2 Verify Free Tier Status
1. **Check Free Tier Usage:**
   - Billing Dashboard → "Free Tier" (left sidebar)
   - You should see available free tier benefits

---

## 🚀 **Step 7: Ready for CLI Configuration**

Once you've completed the above steps, you'll have:
- ✅ IAM user with access keys
- ✅ Key pair for EC2 access
- ✅ Billing alerts configured
- ✅ MFA enabled for security
- ✅ Default region set

### Next: Configure AWS CLI
After completing the console setup, run this in your terminal:

```bash
aws configure
```

Enter:
- **AWS Access Key ID:** [From Step 2.4]
- **AWS Secret Access Key:** [From Step 2.4]  
- **Default region name:** `us-east-1`
- **Default output format:** `json`

---

## 💡 **Important Notes**

### Cost Optimization:
- 🎯 **Always use Spot Instances** (70% cheaper)
- 🎯 **Stop instances when not in use**
- 🎯 **Set up S3 lifecycle policies**
- 🎯 **Monitor costs weekly**

### Security Best Practices:
- 🔒 **Never use root credentials for CLI**
- 🔒 **Enable MFA on all accounts**
- 🔒 **Rotate access keys regularly**
- 🔒 **Use least privilege principle**

### Emergency Actions:
- 🚨 **If costs spike:** Stop all EC2 instances immediately
- 🚨 **If security breach:** Rotate all access keys
- 🚨 **If locked out:** Use root account to reset

---

## 🆘 **Troubleshooting**

### Common Issues:
1. **"Access Denied" errors:** Check IAM permissions
2. **"Invalid credentials":** Verify access keys in `aws configure`
3. **"Region not found":** Ensure region is set to `us-east-1`
4. **High costs:** Check EC2 instances and stop unused ones

### Getting Help:
- 📞 **AWS Support:** Basic plan includes billing support
- 📧 **Account issues:** Use root account recovery
- 💬 **Community:** AWS re:Post forum

---

## ✅ **Checklist Before Deployment**

Before running our deployment script, ensure:
- [ ] IAM user created with proper permissions
- [ ] Access keys downloaded and secured
- [ ] Key pair created and .pem file saved
- [ ] Billing alerts configured
- [ ] MFA enabled
- [ ] AWS CLI configured with `aws configure`
- [ ] Test CLI: `aws sts get-caller-identity`

**Once this checklist is complete, you're ready to deploy!** 🚀