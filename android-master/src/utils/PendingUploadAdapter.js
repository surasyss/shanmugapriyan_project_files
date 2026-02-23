import Adapter from './Adapter';

class PendingUploadAdapter {
    static PENDING_UPLOADS = 'pending_uploads';

    static async getPendingUploadsData() {
      try {
        let data = await Adapter.get(this.PENDING_UPLOADS);
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

    static async getPendingUploads() {
      try {
        let data = await Adapter.get(this.PENDING_UPLOADS);
        if (!data) data = [];
        return data;
      } catch (e) {
        return [];
      }
    }

    static async addPendingUpload(restaurant, image, takenAt, signedUrl, options) {
      const data = {
        restaurant,
        image,
        takenAt,
        signedUrl,
        options
      };

      const uploads = await this.getPendingUploads();
      uploads.push(image);

      await Adapter.set(image, data);
      await Adapter.set(this.PENDING_UPLOADS, uploads);
      return data;
    }

    static async updatePendingUploads(invoice, values) {
      const upload = await Adapter.get(invoice.image);
      if (upload) {
        Object.keys(values).forEach((key) => {
          upload[key] = values[key];
        });
        await Adapter.set(invoice.image, upload);
      }
    }

    static async deleteCreatedInvoice() {
      const pendingUploads = await this.getPendingUploads();
      const remainingUploads = [];

      // eslint-disable-next-line no-restricted-syntax
      for (const pendingUpload of pendingUploads) {
        const invoice = await Adapter.get(pendingUpload);
        if (invoice && invoice.isCreated) {
          await Adapter.remove(pendingUpload);
        } else {
          remainingUploads.push(pendingUpload);
        }
      }
      await Adapter.set(this.PENDING_UPLOADS, remainingUploads);
    }

    static async deleteInvoice(invoice) {
      const pendingUploads = await this.getPendingUploads();
      const { image } = invoice;
      const remainingUploads = [];

      // eslint-disable-next-line no-restricted-syntax
      for (const pendingUpload of pendingUploads) {
        if (pendingUpload && pendingUpload === image) {
          await Adapter.remove(pendingUpload);
        } else {
          remainingUploads.push(pendingUpload);
        }
      }
      await Adapter.set(this.PENDING_UPLOADS, remainingUploads);
    }
}

export default PendingUploadAdapter;
