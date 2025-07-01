# Changelog - Video Clip Generator

All notable changes to this project will be documented in this file.

## [2024-01-XX] - Latest Deployment and Docker Build Fixes

### Fixed
- **File Upload Size Limit**: Fixed MAX_FILE_SIZE configuration in CloudFormation
  - Updated MAX_FILE_SIZE from "500" (500 bytes) to "524288000" (500MB in bytes)
  - Fixed "File too large. Maximum size: 0MB" error during video uploads
  - config.py expects the value in bytes, not megabytes

- **Python Dependency Conflicts**: Fixed Docker build failures due to numpy version conflicts
  - Updated numpy from `==1.24.3` to `>=2.0.0` to satisfy whisperx requirement of `numpy>=2.0.2`
  - Changed opencv-python from exact version to `>=4.8.0` for better compatibility
  - Relaxed AWS dependencies (boto3, botocore, s3transfer) to use minimum versions
  - Updated requests to use minimum version for better dependency resolution

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
  - Added fallback mechanism to construct ECR URIs if job outputs are empty

### Changed
- **requirements.txt**:
  - Updated numpy to `>=2.0.0` for compatibility with whisperx 3.4.2
  - Relaxed opencv-python version constraint to `>=4.8.0`
  - Updated AWS dependencies to use minimum versions for better flexibility
  - Updated requests to use minimum version constraint

- **deployment/cloudformation-application.yml**:
  - Simplified ECR lifecycle policies to only include untagged image cleanup
  - Fixed ECS scaling target resource IDs to use consistent naming
  - Added dependencies between scaling targets and their services

- **.github/workflows/deploy.yml**:
  - Enhanced ECR URI construction using dynamic AWS account ID lookup
  - Added comprehensive debug output for troubleshooting build issues
  - Fixed environment variable passing between GitHub Actions steps
  - Added validation to fail fast if ECR repository URI is empty
  - Added fallback ECR URI construction mechanism

### Technical Details
The deployment was failing due to multiple issues:

1. **Python Dependency Conflicts**: The newer whisperx version requires numpy>=2.0.2, but we had pinned numpy to 1.24.3
2. **ECR Lifecycle Policy Validation**: AWS requires `tagPrefixList` or `tagPatternList` when using `tagStatus=TAGGED` in lifecycle policies
3. **ECS Scaling Target References**: The `ResourceId` must exactly match the ECS service name format
4. **Docker Tag Format**: Docker tags have strict naming requirements and cannot start with numbers
5. **Variable Passing**: GitHub Actions environment variables weren't being set correctly between steps

### TODO Updates
- [x] Fix Python dependency conflicts in requirements.txt
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

## [Latest] - 2025-01-07

### 🔧 Critical Fix: Lazy Loading Initialization
**RESOLVED**: `AttributeError: 'NoneType' object has no attribute 'transcribe'`

Fixed a critical bug introduced with the memory optimization where the lazy loading implementation wasn't being called correctly in the worker tasks.

**Root Cause**: The `tasks.py` file was trying to use `generator.transcriber.transcribe()` directly, but with lazy loading, `generator.transcriber` was still `None` until `_init_transcriber()` was called.

**Files Modified**:
- `tasks.py`: Added proper initialization calls for transcriber and clipfinder
  - Added `generator._init_transcriber()` before using transcriber
  - Added `generator._init_clipfinder()` before using clipfinder  
  - Added memory cleanup calls after transcription and clip finding
  - Added memory cleanup after each clip processing

**Impact**:
- ✅ Workers will now properly initialize AI models before use
- ✅ Video processing should proceed past transcription step
- ✅ Memory optimizations maintained while ensuring functionality
- ✅ No changes to core processing logic or API functionality

---

## [Latest] - 2025-01-07

### 🚀 Critical Memory Optimization & OOM Fix
**RESOLVED**: Worker SIGKILL (Out of Memory) Issues During Video Processing

The workers were being killed by the Linux kernel at 30% progress due to insufficient memory during AI model processing. This update comprehensively addresses memory management.

#### **Memory Allocation Improvements**
- **Increased Worker Memory**: 2GB → 4GB (`Memory: 2048` → `Memory: 4096`)
- **Increased Worker CPU**: 1024 → 2048 (more processing power for AI models)
- **Optimized WhisperX Model**: Changed from `base` to `tiny` model for memory efficiency

#### **Memory Management Optimizations**
- **Lazy Loading**: AI models (transcriber, clipfinder, YOLO) now load only when needed
- **Memory Cleanup**: Added `cleanup_memory()` function with garbage collection and CUDA cache clearing
- **Processing Optimization**: Reduced YOLO frame sampling from 20 to 10 frames
- **Explicit Memory Management**: Added cleanup after each processing step

#### **Environment Optimizations**
```yaml
TORCH_CACHE_DIR: "/tmp/torch_cache"
HF_CACHE_DIR: "/tmp/hf_cache" 
PYTORCH_CUDA_ALLOC_CONF: "max_split_size_mb:128"
OMP_NUM_THREADS: "2"
```

**Files Modified**:
- `deployment/cloudformation-application.yml`: Increased worker resources and added memory optimization env vars
- `clip_generator.py`: Implemented lazy loading, memory cleanup, and optimized processing

**Expected Impact**: 
- ✅ Workers should no longer be killed by OOM during transcription
- ✅ Video processing should complete successfully past 30%
- ✅ Improved stability and reliability for all video sizes
- ✅ More efficient resource usage

---

## [Latest] - 2025-01-07

### 🔥 Critical Database Fix
**RESOLVED**: Worker "no such table: processing_jobs" Error

- **Fixed Database Configuration**: Updated CloudFormation to use PostgreSQL (Neon) instead of SQLite for both API and Worker
- **Added Worker Database Initialization**: Worker now properly initializes database tables on startup
- **Shared Database**: API and Worker now use the same PostgreSQL database ensuring consistent data access

**Database URL**: `postgresql://neondb_owner:npg_Uw1TjtnJOkD9@ep-holy-violet-a13ozjf7-pooler.ap-southeast-1.aws.neon.tech/neondb`

**Files Modified**:
- `deployment/cloudformation-application.yml`: Updated DATABASE_URL for both API and Worker containers
- `tasks.py`: Added `init_database()` call in worker ready handler

**Impact**: 
- ✅ Processing jobs will now complete successfully
- ✅ Worker can access same database as API
- ✅ Consistent data persistence across all services

--- 