import axios from 'axios';

// The backend API base URL is handled by the Vite proxy in development
const API_BASE = '';

/**
 * Sends files and form parameters to the FastAPI /api/process endpoint.
 * 
 * @param {File} file - Medical report file (PDF/Image)
 * @param {File|null} studyImage - High-tech image (PNG/JPEG)
 * @param {string} language - ISO code for target language (es, ca, va, gl, eu)
 * @param {boolean} describeImage - Flag to enable LLM multimodal image description
 * @param {boolean} anonymize - Flag to enable text anonymization after OCR
 */
export const processReport = async (file, studyImage, language, describeImage, anonymize, imageDescription = null, patientId = '', accessionNum = '', studyDesc = '') => {
  const formData = new FormData();
  formData.append('file', file);
  if (studyImage) {
    formData.append('study_image', studyImage);
  }
  formData.append('language', language);
  formData.append('describe_image', describeImage);
  formData.append('anonymize', anonymize);
  if (imageDescription) {
    formData.append('image_description', imageDescription);
  }
  if (patientId) {
    formData.append('patient_id', patientId);
  }
  if (accessionNum) {
    formData.append('accession_num', accessionNum);
  }
  if (studyDesc) {
    formData.append('study_desc', studyDesc);
  }

  const response = await axios.post(`${API_BASE}/api/process`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Sends a study image to the FastAPI /api/describe-image endpoint.
 */
export const describeImageApi = async (studyImage) => {
  const formData = new FormData();
  formData.append('image', studyImage);
  const response = await axios.post(`${API_BASE}/api/describe-image`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Checks backend health status.
 */
export const checkHealth = async () => {
  const response = await axios.get(`${API_BASE}/api/status`);
  return response.data;
};
