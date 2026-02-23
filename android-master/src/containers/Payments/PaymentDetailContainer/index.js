import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  Image, TouchableOpacity, View, BackHandler, InteractionManager
} from 'react-native';
import { HeaderBackButton } from 'react-navigation-stack';
import { StackActions } from 'react-navigation';
import styles from './styles';
import Images from '../../../styles/Images';
import Adapter from '../../../utils/Adapter';
import {
  setCurrentPayment, approvePayment, loadInvoiceDetailsStatic
} from '../../../actions';
import PaymentDetail from '../../../components/Payments/PaymentDetail';

class PaymentDetailContainer extends Component {
  static navigationOptions = ({ navigation }) => {
    let title = '';
    const { params } = navigation.state;
    let offsetPayment = null;
    let handleBackPress = null;

    if (params) {
      title = params.title;
      offsetPayment = params.offsetPayment;
      handleBackPress = params.handleBackPress;
    }

    return {
      title,
      headerRight: (
        <View style={styles.headerButtons}>
          <TouchableOpacity onPress={() => {
            if (offsetPayment) {
              offsetPayment(-1);
            }
          }}
          >
            <Image
              source={Images.up}
              style={styles.up}
              resizeMode="contain"
            />
          </TouchableOpacity>

          <TouchableOpacity onPress={() => {
            if (offsetPayment) {
              offsetPayment(1);
            }
          }}
          >
            <Image
              source={Images.down}
              style={styles.down}
              resizeMode="contain"
            />
          </TouchableOpacity>
        </View>
      ),
      headerLeft: (
        <HeaderBackButton onPress={() => {
          if (handleBackPress) {
            handleBackPress(navigation);
          }
        }}
        />),
      gesturesEnabled: false,
    };
  };

  constructor(props) {
    super(props);
    const { index, type } = props.navigation.state.params;
    this.state = {
      index,
      type,
      canApprove: false,
      restaurants: [],
      isReady: false,
      isShowFlagDialog: false,
      flagText: '',
      isLoading: false,
    };
  }

  async componentDidMount() {
    const restaurants = await Adapter.getRestaurants();
    const user = await Adapter.getUser();
    const { permissions } = user;

    this.setState({ restaurants, canApprove: permissions.indexOf('billpay.change_approval') !== -1 });
    this.props.navigation.setParams({
      offsetPayment: this.offsetPayment,
      handleBackPress: this.handleBackPress,
    });
    this.setPayment();
    this.backHandler = BackHandler.addEventListener('hardwareBackPress', this.handleBackPress);

    InteractionManager.runAfterInteractions(() => {
      this.setState({
        isReady: true
      });
    });
  }

  componentWillUnmount() {
    this.backHandler.remove();
  }

  onBackPress = () => this.handleBackPress();

  getPayment() {
    const { index, type } = this.state;
    if (type === 'pending') return this.props.pendingPayments.data[index];
    if (type === 'all') return this.props.allPayments.data[index];
    return [];
  }

  setPayment() {
    const { index, type } = this.state;
    let netLength = 0;

    if (type === 'pending') netLength = this.props.pendingPayments.data.length;
    if (type === 'all') netLength = this.props.allPayments.data.length;

    const title = `${index + 1} / ${netLength}`;
    this.props.navigation.setParams({ title });

    const payment = this.getPayment();
    this.setState({ payment });
  }

  handleBackPress = () => {
    const popAction = StackActions.popToTop({ immediate: true });
    this.props.navigation.dispatch(popAction);
    return true;
  };

  offsetPayment = async (offset) => {
    let { index } = this.state;
    const { type } = this.state;
    let netLength = 0;

    let payments = [];
    if (type === 'pending') payments = this.props.pendingPayments.data;
    if (type === 'all') payments = this.props.allPayments.data;

    netLength = payments.length;
    index += offset;
    const canChange = !this.props.paymentDetail.currentPayment || this.props.paymentDetail.currentPayment === index - offset;

    if (index >= 0 && index < netLength && canChange) {
      this.props.setCurrentPayment(index);
      const title = `${index + 1} / ${netLength}`;
      this.props.navigation.push('PaymentDetail', {
        type, index, offsetPayment: this.offsetPayment, title
      });
    }
  };

  loadInvoice = async (invoice_id) => {
    this.setState({ isLoading: true });
    const invoice = await loadInvoiceDetailsStatic(invoice_id);
    this.setState({ isLoading: false });
    this.props.navigation.navigate('InvoiceDetailStatic', {
      invoice
    });
  };

  render() {
    const {
      payment, restaurants, canApprove, isLoading
    } = this.state;
    const { approvePayment } = this.props;

    if (!this.state.isReady) {
      return <View />;
    }

    return (
      <PaymentDetail
        payment={payment}
        restaurants={restaurants}
        canApprove={canApprove}
        approvePayment={approvePayment}
        loadInvoice={this.loadInvoice}
        isLoading={isLoading}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  pendingPayments: state.pendingPayments,
  allPayments: state.allPayments,
  paymentDetail: state.paymentDetail
});

export default connect(
  mapStateToProps,
  {
    setCurrentPayment, approvePayment
  }
)(PaymentDetailContainer);
