import React, { Component } from 'react';
import {
  View, Image, FlatList
} from 'react-native';
import ActionSheet from 'react-native-actionsheet';
import styles from './styles';
import Images from '../../../styles/Images';
import Button from '../../qubiqle/Button';
import PendingUpload from '../PendingUpload';
import { showWarningToast } from '../../../utils/Toaster';

export default class UploadInvoice extends Component {
  async showActionSheet() {
    const { refreshRestaurants } = this.props;
    if (!this.ActionSheet) await refreshRestaurants();
    const { restaurants } = this.props;
    if (restaurants) {
      if (restaurants.length) {
        if (this.ActionSheet) this.ActionSheet.show();
      } else {
        showWarningToast("You don't have any locations");
      }
    }
  }

  renderPendingList() {
    const { data, onInvoiceDelete } = this.props;
    if (data && data.length) {
      return (
        <View style={styles.container}>
          <FlatList
            style={styles.pendingUploads}
            data={data}
            renderItem={({ item }) => {
              const {
                restaurant, image, options, signedUrl, takenAt, loading, uploadPercentage, isUploaded, isCreated
              } = item;
              return (
                <PendingUpload
                  restaurant={restaurant}
                  image={image}
                  options={options}
                  signedUrl={signedUrl}
                  takenAt={takenAt}
                  loading={loading}
                  uploadPercentage={uploadPercentage}
                  isUploaded={isUploaded}
                  isCreated={isCreated}
                  onPress={onInvoiceDelete}
                  invoice={item}
                />
              );
            }}
          />
          <View style={styles.bottomView}>
            {this.renderUploadButton()}
            {this.renderUploadReceiptButton()}
          </View>
        </View>

      );
    }
    return (
      <View />
    );
  }

  renderBlank() {
    const { data } = this.props;
    if (!data || data.length === 0) {
      return (
        <View style={styles.blankContainer}>
          <Image
            source={Images.icon_no_invoices}
            resizeMode="contain"
            style={styles.blankImage}
          />
          {this.renderUploadButton()}
          {this.renderUploadReceiptButton()}
        </View>
      );
    }
    return (
      <View />
    );
  }

  renderUploadButton() {
    const { canUploadInvoice } = this.props;
    if (canUploadInvoice) {
      return (
        <Button
          type="primary"
          title="Upload Invoices"
          style={styles.blankButton}
          onPress={async () => this.showActionSheet()}
        />
      );
    }
    return null;
  }

  renderUploadReceiptButton() {
    const { showTransactions, onReceiptUpload } = this.props;
    if (showTransactions) {
      return (
        <Button
          type="outline"
          title="Upload Receipt"
          style={styles.blankReceiptButton}
          onPress={onReceiptUpload}
        />
      );
    }
    return null;
  }

  renderActionSheet() {
    const CANCEL_INDEX = 0;
    const { restaurants, selectRestaurant } = this.props;
    if (restaurants) {
      const options = restaurants.map((restaurant) => restaurant.name);
      options.unshift('Cancel');
      const title = 'Please pick a Location';

      return (
        <View>
          <ActionSheet
            ref={(o) => {
              this.ActionSheet = o;
            }}
            title={title}
            options={options}
            cancelButtonIndex={CANCEL_INDEX}
            onPress={(index) => {
              selectRestaurant(restaurants[index - 1]);
            }}
          />
        </View>
      );
    }
    return (
      <View />
    );
  }

  render() {
    return (
      <View style={styles.container}>
        {this.renderBlank()}
        {this.renderPendingList()}
        {this.renderActionSheet()}
      </View>
    );
  }
}
