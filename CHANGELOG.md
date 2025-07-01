# Changelog - Video Clip Generator

All notable changes to this project will be documented in this file.

## [2024-01-XX] - Latest Deployment and Docker Build Fixes

### Fixed
- **ECR Lifecycle Policy Issues**: Fixed invalid lifecycle policies in CloudFormation
  - Removed problematic "tagged" image rules that required `tagPrefixList` or `tagPatternList`
  - Kept only valid "untagged" image cleanup rules to remove old untagged images after 1 day
  - Fixed both API and Worker ECR repository lifecycle policies

- **ECS Service Auto Scaling Issues**: Fixed scaling target resource references
  - Corrected `ResourceId` format in `APIScalableTarget` and `WorkerScalableTarget`
  - Changed from `service/vcg-${Environment}/vcg-${Environment}-api` to `service/${ProjectName}-${Environment}/${ProjectName}-${Environment}-api`
  - Added `DependsOn` properties to ensure scaling targets are created after their respective services

- **Docker Image Tag Format Issues**: Fixed invalid Docker tag format in GitHub Actions
  - Added "sha-" prefix to git commit hash to ensure valid Docker tag format
  - Changed from `IMAGE_TAG: ${{ github.sha }}` to `IMAGE_TAG: sha-${{ github.sha }}`
  - Docker tags must start with a letter, not a number

- **ECR Repository URI Resolution**: Fixed empty ECR repository URI in build process
  - Modified GitHub Actions workflow to construct ECR URIs directly using AWS account ID
  - Changed from retrieving URIs from CloudFormation outputs to building them dynamically
  - Fixed order of operations: get AWS account ID → construct URIs → use in build process
  - Added debug output to troubleshoot ECR URI issues

### Changed
- **deployment/cloudformation-application.yml**:
  - Simplified ECR lifecycle policies to only include untagged image cleanup
  - Fixed ECS scaling target resource IDs to use consistent naming
  - Added dependencies between scaling targets and their services

- **.github/workflows/deploy.yml**:
  - Enhanced ECR URI construction using dynamic AWS account ID lookup
  - Added comprehensive debug output for troubleshooting build issues
  - Fixed environment variable passing between GitHub Actions steps
  - Added validation to fail fast if ECR repository URI is empty

### Technical Details
The deployment was failing due to multiple issues:

1. **ECR Lifecycle Policy Validation**: AWS requires `tagPrefixList` or `tagPatternList` when using `tagStatus=TAGGED` in lifecycle policies
2. **ECS Scaling Target References**: The `ResourceId` must exactly match the ECS service name format
3. **Docker Tag Format**: Docker tags have strict naming requirements and cannot start with numbers
4. **Variable Passing**: GitHub Actions environment variables weren't being set correctly between steps

### TODO Updates
- [x] Fix ECR lifecycle policy validation errors
- [x] Fix ECS service scaling target resource references
- [x] Fix Docker image tag format issues
- [x] Fix ECR repository URI resolution in build process
- [x] Add debug output for troubleshooting
- [ ] Monitor deployment for successful completion
- [ ] Verify all services are running correctly after deployment

## [2024-01-XX] - CI/CD Build and Deployment Fixes

### Fixed
- **GitHub Actions CI Build Failure**: Resolved import errors in build-and-test phase
  - Added `opencv-python==4.8.1.78` to basic CI dependencies
  - Added `numpy==1.24.3` to basic CI dependencies
  - Updated import tests to handle heavy ML dependencies gracefully
  - Split import tests to isolate core modules from ML-dependent modules

- **CloudFormation Template Error**: Fixed Redis cluster endpoint reference
  - Changed `RedisCluster.RedisEndpoint.Address` to `RedisCluster.PrimaryEndPoint.Address`
  - ElastiCache ReplicationGroup uses `PrimaryEndPoint.Address` not `RedisEndpoint.Address`

- **Deployment Order Issue**: Fixed infrastructure deployment sequence
  - Split deployment into phases: infrastructure → build images → deploy services  
  - Application stack initially deploys with DesiredCount=0 to create ECR repos
  - Services are scaled up only after Docker images are built and pushed
  - Fixed cleanup-on-failure to handle missing clusters/services gracefully

- **Stack State Management**: Added robust stack state handling
  - Auto-detect and delete stacks in ROLLBACK_COMPLETE state
  - Added proper stack deletion order (application before infrastructure)
  - Enhanced error handling for stack state transitions
  - Added comprehensive cleanup for failed deployments

- Fixed Redis configuration in CloudFormation template:
  - Changed `SubnetGroupName` to `CacheSubnetGroupName`
  - Disabled encryption features to simplify deployment
  - Added `AutomaticFailoverEnabled: false` for single-node setup
- Enhanced deployment script with better error reporting for CloudFormation failures

### Changed
- **.github/workflows/deploy.yml**:
  - Enhanced basic dependency installation to include OpenCV and NumPy
  - Improved import test error handling for missing ML dependencies
  - Separated core module testing from heavy ML dependency testing

- **requirements.txt**:
  - Pinned `opencv-python` to version 4.8.1.78 for reproducibility
  - Pinned `numpy` to version 1.24.3 for consistency

### Added
- **ARCHITECTURE_BLUEPRINT.md**: Created project architecture documentation
- **CHANGELOG.md**: Created this changelog to track project changes

### Technical Details
The CI was failing because `cv2` (OpenCV) wasn't available when trying to import the complete module chain. The import chain was:
```
main.py → tasks.py → clip_generator.py → cv2 (missing)
```

The fix ensures OpenCV and NumPy are available in CI while still allowing heavy ML dependencies (torch, ultralytics, clipsai, whisperx) to be optional in the build environment.

## [Previous Deployment Infrastructure Fixes]

### Fixed
- Major improvements to deployment script reliability:
  - Added proper stack existence checking
  - Removed misleading `--no-fail-on-empty-changeset` flag
  - Added infrastructure stack output verification
  - Added detailed error reporting for both stacks
  - Added proper status checking before operations
- Updated cross-stack references in application stack:
  - Changed all ImportValue references to use `vcg` prefix
  - Updated default project name to `vcg`
  - Fixed references to ECS, Redis, and networking resources
- Improved stack deletion process:
  - Added detailed progress monitoring during stack deletion
  - Added resource listing before deletion
  - Added periodic status updates during deletion
  - Improved error handling and logging
- Enhanced deployment script to handle existing stacks:
  - Added cleanup of old stacks with previous naming convention
  - Created reusable stack deletion function
  - Improved error handling and logging
- Removed unsupported `MultiAZ` property from Redis configuration
- Fixed Redis configuration property names in CloudFormation template:
  - Changed `Description` to `ReplicationGroupDescription`
  - Changed `NodeType` to `CacheNodeType`
- Shortened AWS resource names to comply with length limits:
  - Changed target group name to `vcg-{environment}-tg`
  - Changed load balancer name to `vcg-{environment}-alb`
  - Changed Redis cluster name to `vcg-{environment}-redis`
  - Changed ECS cluster name to `vcg-{environment}`
- Fixed Redis configuration in CloudFormation template:
  - Changed `SubnetGroupName` to `CacheSubnetGroupName`
  - Disabled encryption features to simplify deployment
  - Added `AutomaticFailoverEnabled: false` for single-node setup
- Enhanced deployment script with better error reporting for CloudFormation failures 