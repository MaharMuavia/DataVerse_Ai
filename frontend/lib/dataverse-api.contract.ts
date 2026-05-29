import {
  API_BASE_URL,
  streamQuery,
  uploadDataset,
  type ChatEvent,
  type UploadResponse,
} from './dataverse-api';

async function contract(file: File): Promise<void> {
  const uploaded: UploadResponse = await uploadDataset(file);
  const events: ChatEvent[] = await streamQuery(uploaded.session_id, 'summarize this dataset');

  API_BASE_URL.toString();
  uploaded.column_names?.map((column) => column.toLowerCase());
  events.map((event) => event.step);
}

void contract;
