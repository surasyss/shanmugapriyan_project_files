import React, { Component } from 'react';
import { connect } from 'react-redux';
import { BackHandler, InteractionManager, View } from 'react-native';
import { HeaderBackButton } from 'react-navigation-stack';
import { StackActions } from 'react-navigation';
import {
  addReceiptInCurrentAllTransaction,
  addReceiptInCurrentPendingTransaction,
  setCurrentTransaction,
  updatePendingReceiptProgress,
  updateReceiptProgress
} from '../../../actions';
import TransactionDetail from '../../../components/Transactions/TransactionDetail';
import Adapter from '../../../utils/Adapter';

class TransactionDetailContainer extends Component {
  static navigationOptions = ({ navigation }) => {
    let title = '';
    const { params } = navigation.state;
    // let offsetTransaction = null;
    let handleBackPress = null;

    if (params) {
      title = params.title;
      // offsetTransaction = params.offsetTransaction;
      handleBackPress = params.handleBackPress;
    }

    return {
      title,
      // headerRight: (
      //   <View style={styles.headerButtons}>
      //     <TouchableOpacity onPress={() => {
      //       if (offsetTransaction) {
      //         offsetTransaction(-1);
      //       }
      //     }}
      //     >
      //       <Image
      //         source={Images.up}
      //         style={styles.up}
      //         resizeMode="contain"
      //       />
      //     </TouchableOpacity>
      //
      //     <TouchableOpacity onPress={() => {
      //       if (offsetTransaction) {
      //         offsetTransaction(1);
      //       }
      //     }}
      //     >
      //       <Image
      //         source={Images.down}
      //         style={styles.down}
      //         resizeMode="contain"
      //       />
      //     </TouchableOpacity>
      //   </View>
      // ),
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
      isReady: false,
      transaction: null,
      user: null,
    };
  }

  async componentDidMount() {
    this.props.navigation.setParams({
      offsetTransaction: this.offsetTransaction,
      handleBackPress: this.handleBackPress,
    });
    this.setTransaction();
    this.backHandler = BackHandler.addEventListener('hardwareBackPress', this.handleBackPress);

    InteractionManager.runAfterInteractions(() => {
      this.setState({
        isReady: true
      });
    });

    const user = await Adapter.getUser();
    this.setState({ user });
  }

  componentWillUnmount() {
    this.backHandler.remove();
  }

  getTransaction() {
    const { index, type } = this.state;
    if (type === 'pending') return this.props.pendingTransactions.data[index];
    if (type === 'all') return this.props.allTransactions.data[index];
    return {};
  }

  setTransaction() {
    const { index, type } = this.state;
    let netLength = 0;

    if (type === 'pending') netLength = this.props.pendingTransactions.data.length;
    if (type === 'all') netLength = this.props.allTransactions.data.length;

    const title = `${index + 1} / ${netLength}`;
    this.props.navigation.setParams({ title });

    const transaction = this.getTransaction();
    this.setState({ transaction });
  }

  handleBackPress = () => {
    const popAction = StackActions.popToTop({ immediate: true });
    this.props.navigation.dispatch(popAction);
    return true;
  };

  offsetTransaction = async (offset) => {
    let { index } = this.state;
    const { type } = this.state;
    let netLength = 0;

    let transactions = [];
    if (type === 'pending') transactions = this.props.pendingTransactions.data;
    if (type === 'all') transactions = this.props.allTransactions.data;

    netLength = transactions.length;
    index += offset;
    const canChange = !this.props.transactionDetail.currentTransaction || this.props.transactionDetail.currentTransaction === index - offset;

    if (index >= 0 && index < netLength && canChange) {
      this.props.setCurrentTransaction(index);
      const title = `${index + 1} / ${netLength}`;
      this.props.navigation.push('TransactionDetail', {
        type, index, offsetTransaction: this.offsetTransaction, title
      });
    }
  };

  goToAddReceipt = () => {
    const { transaction, index, type } = this.state;
    this.props.navigation.navigate('ReceiptCamera', { transaction, index, type });
  };

  render() {
    const { user } = this.state;
    const { uploads } = this.props;
    const transaction = this.getTransaction();
    if (!this.state.isReady) {
      return <View />;
    }

    return (
      <TransactionDetail
        user={user}
        pendingUploads={uploads.data}
        transaction={transaction}
        goToAddReceipt={this.goToAddReceipt}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  pendingTransactions: state.pendingReceiptTransactions,
  allTransactions: state.allTransactions,
  transactionDetail: state.transactionDetail,
  uploads: state.pendingTransactionReceipts,
});

export default connect(
  mapStateToProps,
  {
    setCurrentTransaction, updateReceiptProgress, updatePendingReceiptProgress, addReceiptInCurrentAllTransaction, addReceiptInCurrentPendingTransaction
  }
)(TransactionDetailContainer);
