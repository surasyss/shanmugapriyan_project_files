import React, { Component } from 'react';
import { connect } from 'react-redux';
import { Dimensions } from 'react-native';
import ImagePicker from 'react-native-image-crop-picker';
import ReceiptCamera from '../../../components/Transactions/ReceiptCamera';
import { loadUnassignedReceipts } from '../../../actions';

class ReceiptCameraContainer extends Component {
  constructor(props) {
    super(props);
    this.state = {
      index: 0,
    };
  }

  componentDidMount() {
    this.refreshUnassignedReceipts();
  }

  refreshUnassignedReceipts = () => {
    const {
      transaction
    } = this.props.navigation.state.params;
    const { card } = transaction;
    const { company } = card;
    const { remote_id } = company;
    this.props.loadUnassignedReceipts(remote_id);
  };

  selectScene = (index) => {
    this.setState({ index });
  }

  goBack = () => {
    this.props.navigation.goBack();
  }

  goToPreview = (image) => {
    const {
      transaction, index, type, refreshTransactions
    } = this.props.navigation.state.params;
    this.props.navigation.navigate('ReceiptPreviewPage', {
      image, transaction, index, type, refreshTransactions
    });
  };

  openUnassigned = (image) => {
    const {
      transaction, index, type, refreshTransactions
    } = this.props.navigation.state.params;
    this.props.navigation.navigate('ReceiptPreviewPage', {
      image,
      transaction,
      index,
      type,
      refreshTransactions,
      unassigned: true,
      refreshUnassignedReceipts: this.refreshUnassignedReceipts,
    });
  }

  takePicture = async (camera) => {
    const options = { base64: true };
    if (camera) {
      try {
        const { uri } = await camera.takePictureAsync(options);
        this.goToPreview(uri);
      } catch (e) {

      }
    }
  };

  openGallery = () => {
    const { width } = Dimensions.get('window');
    ImagePicker.openPicker({
      width,
      height: width,
      cropping: true
    }).then((image) => {
      const { path } = image;
      this.goToPreview(path);
    });
  };

  render() {
    const { index } = this.state;
    return (
      <ReceiptCamera
        index={index}
        goBack={this.goBack}
        takePicture={this.takePicture}
        goToPreview={this.goToPreview}
        openGallery={this.openGallery}
        selectScene={this.selectScene}
        receipts={this.props.receipts}
        openUnassigned={this.openUnassigned}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  receipts: state.unassignedReceipts.data
});

export default connect(
  mapStateToProps, { loadUnassignedReceipts }
)(ReceiptCameraContainer);
