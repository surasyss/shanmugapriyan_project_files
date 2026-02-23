import React from 'react';
import {
  View, Text, ScrollView, Image, TouchableOpacity
} from 'react-native';
import ImageView from 'react-native-image-view';
import Pdf from 'react-native-pdf';
import { withNavigationFocus } from 'react-navigation';
import Modal from 'react-native-modal';
import Icon from 'react-native-vector-icons/dist/FontAwesome5';
import { connect } from 'react-redux';
import { Button, TextInput } from 'react-native-paper';
import styles from './styles';
import { parseTransactionDate } from '../../../utils/DateFormatter';
import { toCurrency } from '../../../utils/StringFormatter';
import Images from '../../../styles/Images';
import Receipt from '../Receipt';
import { addMemo, setEditMemo } from '../../../actions';

class TransactionDetail extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      imageVisible: false,
      uploadVisible: false,
      memoInput: null,
    };
  }

  componentWillUnmount() {
    this.onMemoDiscard();
  }

  closeModal = () => {
    this.setState({ imageVisible: false });
  }

  onClickAddEditMemo = () => {
    this.setState({
      memoInput: this.props.transaction.memo
    });
    this.props.setEditMemo(true);
  }

  onMemoDiscard = () => {
    this.props.setEditMemo(false).then(
      () => this.setState({
        memoInput: null
      })
    );
  }

  onMemoSave = () => {
    const { transaction } = this.props;
    const { id, card, memo } = transaction;
    const { company } = card;
    const { remote_id } = company;
    const trimMemo = this.state.memoInput.trim().length > 0 ? this.state.memoInput.trim() : null;
    if (memo !== trimMemo) {
      this.props.addMemo(id, remote_id, trimMemo);
    } else {
      this.onMemoDiscard();
    }
  }

  renderHeader() {
    const { transaction } = this.props;
    const {
      merchant_name, posting_date, id, computed_amount
    } = transaction;

    return (
      <View>
        <Text style={styles.transactionId}>{id}</Text>
        <View style={styles.transactionHeader}>
          <View style={styles.transactionHeaderLeft}>
            <Text style={styles.merchant}>{merchant_name}</Text>
            <Text style={styles.transactionDate}>
              Posted on:
              {parseTransactionDate(posting_date)}
            </Text>
          </View>
          <Text style={[styles.amount, styles.transactionHeaderRight]}>{toCurrency(computed_amount)}</Text>
        </View>
      </View>
    );
  }

  renderDetails() {
    const { transaction, isEditMemo } = this.props;
    const {
      card, additional_info, merchant_category_name, memo, export_transaction_id
    } = transaction;
    const { last_4, owner } = card;
    const { status } = additional_info;
    return (
      <View style={styles.transactionDetails}>
        <View style={styles.transactionDetailRow}>
          <Text style={styles.transactionDetailLeft}>Status</Text>
          <Text style={styles.transactionDetailRight}>{status}</Text>
        </View>

        <View style={styles.transactionDetailRow}>
          <Text style={styles.transactionDetailLeft}>Cardholder name</Text>
          <Text style={styles.transactionDetailRight}>{owner.display_name}</Text>
        </View>

        <View style={styles.transactionDetailRow}>
          <Text style={styles.transactionDetailLeft}>Card number</Text>
          <Text style={styles.transactionDetailRight}>{`X${last_4}`}</Text>
        </View>

        <View style={styles.transactionDetailRow}>
          <Text style={styles.transactionDetailLeft}>Merchant category</Text>
          <Text style={styles.transactionDetailRight}>{merchant_category_name || 'Unknown Category'}</Text>
        </View>
        {(!export_transaction_id && !memo && !isEditMemo)
          && (
          <TouchableOpacity style={styles.addMemoRow} onPress={this.onClickAddEditMemo}>
            <Icon name="tag" size={15} color={styles.tagIcon.color} />
            <Text style={styles.addMemoText}>Add a memo to this transaction</Text>
          </TouchableOpacity>
          )}
        {isEditMemo
          && (
          <View style={styles.editMemoRow}>
            <Text>Memo</Text>
            <TextInput
              theme={styles.textInputTheme}
              mode="outlined"
              multiline
              numberOfLines={4}
              value={this.state.memoInput}
              onChangeText={(text) => this.setState({ memoInput: text })}
            />
            <View style={styles.memoButtonContainer}>
              <Button mode="outlined" labelStyle={styles.discardLabel} style={styles.discardButton} onPress={this.onMemoDiscard}>
                Discard
              </Button>
              <Button mode="contained" theme={styles.saveButtonTheme} labelStyle={styles.saveButtonLabel} style={styles.saveButton} onPress={this.onMemoSave}>
                Save
              </Button>
            </View>
          </View>
          )}
        {(memo && !isEditMemo)
          && (
          <View style={styles.memoRow}>
            <Text>Memo</Text>
            <View style={styles.memoContainer}>
              <Text style={styles.memoText}>{memo}</Text>
              {!export_transaction_id
                && (
                <TouchableOpacity onPress={this.onClickAddEditMemo}>
                  <Icon name="pencil-alt" size={13} />
                </TouchableOpacity>
                )}
            </View>
          </View>
          )}
      </View>
    );
  }

  renderReceiptHeading() {
    return (
      <View>
        <Text style={styles.receiptsHeading}>Receipts</Text>
      </View>
    );
  }

  renderAddReceiptButton() {
    const { transaction } = this.props;
    return (
      <TouchableOpacity
        style={styles.addReceiptButton}
        onPress={() => {
          this.props.navigation.navigate('ReceiptCamera', {
            transaction
          });
        }}
      >
        <View style={styles.addReceiptIconParent}>
          <Image
            resizeMode="contain"
            source={Images.ic_plus}
            style={styles.addReceiptIcon}
          />
        </View>
        <View>
          <Text style={styles.addReceiptTitle}>Add a receipt</Text>
          <Text style={styles.addReceiptDescription}>You can either upload a receipt or assign one that already has been uploaded</Text>
        </View>
      </TouchableOpacity>
    );
  }

  renderUploadedReceipts() {
    const { transaction } = this.props;
    const { receipts } = transaction;
    return receipts.map((receipt, index) => {
      const { id } = receipt;
      return (
        <Receipt
          key={id}
          receipt={receipt}
          onPress={() => {
            this.setState({ imageVisible: true, index });
          }}
        />
      );
    });
  }

  renderUploadingReceipts() {
    const { transaction, pendingUploads, user } = this.props;
    const receipts = [];
    if (pendingUploads) {
      pendingUploads.forEach((receipt) => {
        const {
          transaction_id, image, takenAt, isCreated, uploadPercentage
        } = receipt;
        if (transaction_id === transaction.id) {
          receipt.file_url = image;
          receipt.progress = uploadPercentage;
          receipt.created_date = takenAt;
          receipt.isCreated = isCreated;
          receipt.created_user_name = user ? user.display_name : '';
          receipts.push(receipt);
        }
      });
      return receipts.map((receipt, index) => {
        const { id } = receipt;
        return (
          <Receipt
            key={id}
            receipt={receipt}
            onPress={() => {
              this.setState({ uploadVisible: true, index });
            }}
          />
        );
      });
    }
    return null;
  }

  renderPdfFile(file_url) {
    const { imageVisible } = this.state;
    return (
      <Modal
        onRequestClose={this.closeModal}
        onBackButtonPress={this.closeModal}
        onBackdropPress={this.closeModal}
        style={styles.pdfModal}
        isVisible={imageVisible}
      >
        <TouchableOpacity style={styles.pdfCloseParent} onPress={() => this.setState({ imageVisible: false })}>
          <Image style={styles.pdfCloseButton} source={Images.camera_close} />
        </TouchableOpacity>
        <Pdf source={{ uri: file_url }} style={{ flex: 1 }} />
      </Modal>
    );
  }

  renderModal() {
    const { imageVisible, index } = this.state;
    let { receipts } = this.props.transaction;

    if (!receipts) receipts = [];
    receipts = receipts.map((res) => ({
      source: {
        uri: res.file_url
      }
    }));

    const extension = receipts[index]?.source?.uri.split('.').reverse()[0];

    if (typeof extension === 'string' && extension.toLowerCase() === 'pdf') {
      return this.renderPdfFile(receipts[index]?.source?.uri);
    }
    return (
      <ImageView
        images={receipts}
        imageIndex={index}
        isVisible={imageVisible}
        onClose={() => this.setState({ imageVisible: false })}
      />
    );
  }

  renderReceiptModal() {
    const { uploadVisible, index } = this.state;
    const { transaction, pendingUploads } = this.props;
    const receipts = [];
    if (pendingUploads) {
      pendingUploads.forEach((receipt) => {
        const {
          transaction_id, image
        } = receipt;
        if (transaction_id === transaction.id) {
          receipts.push({
            source: {
              uri: image
            }
          });
        }
      });
    }

    return (
      <ImageView
        images={receipts}
        imageIndex={index}
        isVisible={uploadVisible}
        onClose={() => this.setState({ uploadVisible: false })}
      />
    );
  }

  render() {
    const { transaction } = this.props;
    if (transaction) {
      return (
        <ScrollView style={styles.container} contentContainerStyle={styles.containerScroll}>
          {this.renderHeader()}
          {this.renderDetails()}
          {this.renderReceiptHeading()}
          {this.renderUploadedReceipts()}
          {this.renderUploadingReceipts()}
          {this.renderAddReceiptButton()}
          {this.renderModal()}
          {this.renderReceiptModal()}
        </ScrollView>
      );
    }
    return <View />;
  }
}

const mapStateToProps = (state) => ({
  isEditMemo: state.transactionDetail.isEditMemo
});

export default withNavigationFocus(
  connect(
    mapStateToProps,
    {
      addMemo, setEditMemo
    }
  )(TransactionDetail)
);
