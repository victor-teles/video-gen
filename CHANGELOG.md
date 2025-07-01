# Changelog - Video Clip Generator

All notable changes to this project will be documented in this file.

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

### TODO Updates
- [x] Fix CI build-and-test phase import errors
- [x] Add OpenCV to basic CI dependencies  
- [x] Pin dependency versions for reproducibility
- [x] Create architecture documentation
- [x] Create changelog documentation
- [ ] Monitor next CI run for successful build
- [ ] Verify deployment pipeline continues to work 

## [Unreleased]

### Fixed
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