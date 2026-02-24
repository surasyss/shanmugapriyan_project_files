import React from 'react';
import {
  View, Text, Image, ActivityIndicator, TouchableOpacity, Platform
} from 'react-native';
import Icon from 'react-native-vector-icons/dist/FontAwesome';
import ScrollableTabView from 'react-native-scrollable-tab-view';
import Pdf from 'react-native-pdf';
import styles from './styles';
import { parserInvoiceDate } from '../../../utils/DateFormatter';
import SwipeButton from '../../qubiqle/SwipeButton/src/components/SwipeButton';
import Colors from '../../../styles/Colors';
import Images from '../../../styles/Images';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import { title, toCurrencyNoSpace } from '../../../utils/StringFormatter';
import DetailsTabBar from '../../qubiqle/DetailsTabBar';
import PaymentInvoiceList from '../../qubiqle/PaymentInvoiceList';
import PaymentChecks from '../../qubiqle/PaymentChecks';
import ModalBox from '../../qubiqle/ModalBox';
import { renderPaymentType } from '../../qubiqle/Payment';
import Spinner from '../../qubiqle/Spinner';

class PaymentDetail extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      isApproved: props.payment.isApproved
    };
  }

  onTabSelection = (index) => {
    const { payment } = this.props;
    if (index.i === 0) sendMixpanelEvent(MixpanelEvents.PAYMENT_INVOICES_OPENED, { payment });
    else if (index.i === 1) sendMixpanelEvent(MixpanelEvents.PAYMENT_CHECK_STUBS_OPENED, { payment });
  };

  renderHeader() {
    const { payment, restaurants } = this.props;
    const {
      vendor_name, scheduled_date, total_amount, id, status
    } = payment;
    let restaurant_name = '';

    if (restaurants) {
      restaurants.forEach((restaurant) => {
        if (restaurant.id === payment.restaurant) {
          restaurant_name = restaurant.name;
        }
      });
    }
    const paymentType = renderPaymentType(payment);
    return (
      <View style={styles.header}>
        <View style={styles.firstHeaderItem}>
          <View style={styles.headerLeft}>
            <Text style={[styles.headerHeading, vendor_name ? {} : styles.missing]}>Payment for </Text>
            <View style={styles.row}>
              <Text style={[paymentType ? styles.vendor : {}, styles.headerValue, vendor_name ? {} : styles.missingValue]}>{vendor_name || 'Missing'}</Text>
              {paymentType ? (
                <View style={[styles.flag, styles.headerValue]}>
                  {renderPaymentType(payment)}
                </View>
              ) : null}
            </View>
          </View>

          <View style={styles.headerRight}>
            <Text style={[styles.headerHeading, styles.right, vendor_name ? {} : styles.missing]}>Status</Text>
            <Text style={[styles.status, styles.right, vendor_name ? {} : styles.missingValue]}>{title(status)}</Text>
          </View>
        </View>

        <View style={styles.headerItem}>
          <Text style={[styles.headerHeading, restaurant_name ? {} : styles.missing]}>Location Name</Text>
          <Text style={[styles.headerValue, restaurant_name ? {} : styles.missingValue]}>{restaurant_name || 'Missing'}</Text>
        </View>

        <View style={styles.lastHeaderItem}>
          <View style={styles.headerInvoiceNumber}>
            <Text style={[styles.headerHeading, id ? {} : styles.missing]}>Reference Number</Text>
            <Text style={[styles.headerValue, id ? {} : styles.missingValue]}>{`CR${id}` || 'Missing'}</Text>
          </View>

          <View style={styles.headerInvoiceDate}>
            <Text style={[styles.headerHeading, styles.centerText, scheduled_date ? {} : styles.missing]}>Scheduled for</Text>
            <Text style={[styles.headerValue, styles.centerText, scheduled_date ? {} : styles.missingValue]}>{parserInvoiceDate(scheduled_date) || 'Missing'}</Text>
          </View>

          <View style={styles.headerInvoiceTotal}>
            <Text style={[styles.headerHeading, styles.rightText]}>Total</Text>
            <Text style={[styles.headerValue, styles.rightText]}>
              {toCurrencyNoSpace(total_amount)}
            </Text>
          </View>
        </View>
      </View>
    );
  }

  renderTabs() {
    const { payment, loadInvoice } = this.props;
    let { invoices } = payment;
    const { payment_info } = payment;
    if (!invoices) invoices = [];
    const images = [];
    if (payment_info && payment_info.payment_info_url) {
      images.push(payment_info.payment_info_url);
    }

    return (
      <ScrollableTabView
        style={{ marginTop: 10 }}
        initialPage={0}
        renderTabBar={() => <DetailsTabBar />}
        onChangeTab={(index) => {
          this.onTabSelection(index);
        }}
      >
        <View tabLabel="Invoices" style={styles.tabView}>
          <PaymentInvoiceList
            invoices={invoices}
            onPress={loadInvoice}
          />
        </View>
        <View tabLabel="Payment Stubs" style={styles.tabView}>
          <PaymentChecks
            images={images}
            onPress={() => {
              this.refs.pdfModal.open();
            }}
          />
        </View>
      </ScrollableTabView>
    );
  }

  renderApproveButton() {
    const { approvePayment, payment, canApprove } = this.props;
    const { status } = payment;
    if (status !== 'pending approval' || !canApprove) {
      return null;
    }

    if (this.state.isApproved) {
      const sliderIcon = () => (
        <Icon
          name="check"
          style={styles.sliderSuccess}
        />
      );

      return (
        <View style={styles.approveButtonParent}>
          <SwipeButton
            disabled
            enableRightToLeftSwipe={this.state.isApproved}
            disabledRailBackgroundColor={Colors.primary}
            disabledThumbIconBackgroundColor={Colors.white}
            thumbIconBackgroundColor={Colors.white}
            thumbIconComponent={sliderIcon}
            title="Swipe to Approve"
            railBackgroundColor={Colors.primary}
            railFillBackgroundColor={Colors.primary}
            railBorderColor={Colors.primary}
            railFillBorderColor={Colors.primary}
            titleColor={Colors.white}
          />
        </View>
      );
    }

    const sliderIcon = () => (
      !payment.isApproved ? <Image source={Images.plate_slider} style={styles.sliderButton} />
        : (
          <Icon
            name="check"
            style={styles.sliderSuccess}
          />
        )
    );
    return (
      <View style={styles.approveButtonParent}>
        <SwipeButton
          disabled={payment.isApproved}
          disabledRailBackgroundColor={Colors.primary}
          disabledThumbIconBackgroundColor={Colors.white}
          thumbIconBackgroundColor={Colors.transparent}
          thumbIconComponent={sliderIcon}
          title="Swipe to Approve"
          onSwipeSuccess={() => {
            let { invoices } = payment;
            if (!invoices) invoices = [];
            const invoice_ids = invoices.map((invoice) => invoice.id);
            approvePayment(payment.id, invoice_ids);
          }}
          railBackgroundColor={Colors.primary}
          railFillBackgroundColor={Colors.primary}
          railBorderColor={Colors.primary}
          railFillBorderColor={Colors.primary}
          titleColor={Colors.white}
        />
      </View>
    );
  }

  renderPdfModal() {
    const { payment } = this.props;
    const { payment_info } = payment;
    if (payment_info) {
      const { payment_info_url } = payment_info;
      return (
        <ModalBox
          coverScreen
          backButtonClose
          style={styles.pdfModal}
          backdrop
          position="center"
          ref="pdfModal"
          swipeToClose={false}
          backdropColor={Colors.backdrop}
          backdropOpacity={1}
        >

          <Pdf
            source={{ uri: payment_info_url }}
            style={styles.pdf}
            activityIndicator={<ActivityIndicator size="small" color={Colors.white} />}
          />

          <TouchableOpacity
            style={styles.closeButton}
            onPress={() => {
              this.refs.pdfModal.close();
            }}
          >
            <Image
              source={Images.camera_close}
              style={styles.closeIcon}
              resizeMode="contain"
            />
          </TouchableOpacity>
        </ModalBox>
      );
    }
    return <View />;
  }

  renderLoadingDialog() {
    const { isLoading } = this.props;
    return (
      <Spinner
        visible={isLoading}
        color={Platform.OS === 'ios' ? Colors.white : Colors.primary}
      />
    );
  }

  render() {
    const { payment } = this.props;

    return (
      <View style={styles.container}>
        {payment ? this.renderHeader() : null}
        {payment ? this.renderTabs() : null}
        {payment ? this.renderApproveButton() : null}
        {payment ? this.renderPdfModal() : null}
        {this.renderLoadingDialog()}
      </View>
    );
  }
}

export default PaymentDetail;
