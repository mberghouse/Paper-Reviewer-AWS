// S3 Direct Upload Functions

// 1. Get upload parameters from backend
async function getUploadParams() {
    try {
      const response = await fetch('/get-upload-params/');
      if (!response.ok) {
        throw new Error(`Failed to get upload parameters: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error getting upload parameters:', error);
      throw error;
    }
  }
  
  // 2. Upload file directly to S3
  async function uploadFileToS3(file, uploadParams) {
    return new Promise((resolve, reject) => {
      // Import AWS SDK - make sure this is included in your HTML
      if (!window.AWS) {
        const script = document.createElement('script');
        script.src = 'aws-sdk';
        script.onload = () => uploadWithAWS();
        script.onerror = () => reject(new Error('Failed to load AWS SDK'));
        document.head.appendChild(script);
      } else {
        uploadWithAWS();
      }
  
      function uploadWithAWS() {
        const { bucket, region, accessKeyId, secretAccessKey, fileKeyPrefix } = uploadParams;
        
        // Configure AWS SDK
        AWS.config.update({
          accessKeyId: accessKeyId,
          secretAccessKey: secretAccessKey,
          region: region
        });
        
        const s3 = new AWS.S3();
        
        // Generate file key
        const fileKey = `${fileKeyPrefix}${file.name}`;
        
        // Upload parameters
        const params = {
          Bucket: bucket,
          Key: fileKey,
          Body: file,
          ContentType: file.type || 'application/pdf'
        };
        
        // Upload to S3
        s3.upload(params, (err, data) => {
          if (err) {
            console.error('S3 upload error:', err);
            reject(err);
          } else {
            resolve({
              fileKey: fileKey,
              location: data.Location
            });
          }
        });
      }
    });
  }
  
  // 3. Register the uploaded file with backend
  async function registerUploadedFile(fileKey) {
    try {
      const response = await fetch('/register-uploaded-file/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ fileKey })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to register file: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error registering file:', error);
      throw error;
    }
  }
  
  // Main upload function that combines all steps
  export async function uploadFile(file) {
    try {
      // 1. Get upload parameters
      const paramsResponse = await getUploadParams();
      if (!paramsResponse.success) {
        throw new Error(paramsResponse.error || 'Failed to get upload parameters');
      }
      
      // 2. Upload to S3
      const uploadResult = await uploadFileToS3(file, paramsResponse.uploadParams);
      
      // 3. Register with backend
      const registrationResult = await registerUploadedFile(uploadResult.fileKey);
      
      return {
        success: true,
        manuscriptId: registrationResult.manuscriptId,
        fileUrl: uploadResult.location
      };
    } catch (error) {
      console.error('Upload process failed:', error);
      return {
        success: false,
        error: error.message || 'Unknown error during upload'
      };
    }
  }