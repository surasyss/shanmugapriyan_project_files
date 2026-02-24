import Adapter from './Adapter';

class PendingTransactionUploadAdapter {
  static PENDING_TRANSACTION_UPLOADS = 'pending_transaction_uploads';

  static async getPendingTransactionUploadsData() {
    try {
      let data = await Adapter.get(this.PENDING_TRANSACTION_UPLOADS);
      if (!data) data = [];

      const uploads = [];

      // eslint-disable-next-line no-restricted-syntax
      for (const image of data) {
        const upload = await Adapter.get(image);
        if (upload) {
          uploads.push(upload);
        }
      }
      return uploads;
    } catch (e) {
      return [];
    }
  }

  static async getPendingTransactionUploads() {
    try {
      let data = await Adapter.get(this.PENDING_TRANSACTION_UPLOADS);
      if (!data) data = [];
      return data;
    } catch (e) {
      return [];
    }
  }

  static async addPendingTransactionUpload(transaction_id, company_id, image, takenAt) {
    const newData = {
      transaction_id,
      company_id,
      image,
      takenAt,
      signedUrl: null,
    };

    const uploads = await this.getPendingTransactionUploads();
    uploads.push(image);

    await Adapter.set(image, newData);
    await Adapter.set(this.PENDING_TRANSACTION_UPLOADS, uploads);
    return newData;
  }

  static async updatePendingTransactionUpload(transaction, values) {
    const upload = await Adapter.get(transaction.image);
    if (upload) {
      Object.keys(values).forEach((key) => {
        upload[key] = values[key];
      });
      await Adapter.set(transaction.image, upload);
    }
  }

  static async deleteCreatedTransactionReceipt() {
    const pendingUploads = await this.getPendingTransactionUploads();
    const remainingUploads = [];

    // eslint-disable-next-line no-restricted-syntax
    for (const pendingUpload of pendingUploads) {
      const transaction = await Adapter.get(pendingUpload);
      if (transaction && transaction.isCreated) {
        await Adapter.remove(pendingUpload);
      } else {
        remainingUploads.push(pendingUpload);
      }
    }
    await Adapter.set(this.PENDING_TRANSACTION_UPLOADS, remainingUploads);
  }

  static async deleteTransaction(transaction) {
    const pendingUploads = await this.getPendingUploads();
    const { image } = transaction;
    const remainingUploads = [];

    // eslint-disable-next-line no-restricted-syntax
    for (const pendingUpload of pendingUploads) {
      if (pendingUpload && pendingUpload === image) {
        await Adapter.remove(pendingUpload);
      } else {
        remainingUploads.push(pendingUpload);
      }
    }
    await Adapter.set(this.PENDING_TRANSACTION_UPLOADS, remainingUploads);
  }
}

export default PendingTransactionUploadAdapter;
