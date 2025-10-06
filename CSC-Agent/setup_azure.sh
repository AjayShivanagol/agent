#!/bin/bash
# Azure SQL Database Setup Script

echo "🔧 Setting up Azure SQL Database Access..."
echo "================================================"

# Step 1: Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Installing..."
    brew install azure-cli
else
    echo "✅ Azure CLI found"
fi

# Step 2: Login to Azure (this will open a browser)
echo ""
echo "🔐 Logging into Azure..."
echo "This will open a browser window for authentication."
read -p "Press Enter to continue..."
az login

# Step 3: Get access token for SQL Database
echo ""
echo "🔑 Getting access token for SQL Database..."
ACCESS_TOKEN=$(az account get-access-token --resource=https://database.windows.net/ --query accessToken --output tsv)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Failed to get access token"
    exit 1
else
    echo "✅ Access token obtained"
fi

# Step 4: Update or insert token in .env using sed
echo ""
echo "📝 Updating .env file with new access token..."

if grep -q "^AZURE_SQL_ACCESS_TOKEN=" .env 2>/dev/null; then
    # Replace existing token
    sed -i '' "s|^AZURE_SQL_ACCESS_TOKEN=.*|AZURE_SQL_ACCESS_TOKEN=$ACCESS_TOKEN|" .env
else
    # Append token if not present
    echo "AZURE_SQL_ACCESS_TOKEN=$ACCESS_TOKEN" >> .env
fi

echo "✅ .env file updated with new Azure access token"
echo ""
echo "🎉 Setup complete! You can now:"
echo "1. Test database connection: python test_quick.py"
echo "2. Start the agent server: python -m app"
echo "3. Search for F920990007514"
echo ""
echo "⚠️  Note: The access token expires periodically. Re-run this script if you get authentication errors."
