import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  Image, TouchableOpacity, View, BackHandler, InteractionManager
} from 'react-native';
import { HeaderBackButton } from 'react-navigation-stack';
import { StackActions } from 'react-navigation';
import Share from 'react-native-share';
import styles from './styles';
import Images from '../../../styles/Images';
import InvoiceDetail from '../../../components/Invoices/InvoiceDetail';
import Adapter from '../../../utils/Adapter';
import {
  loadLineItems, loadGlSplits, loadInvoiceImages, approveInvoice, loadInvoiceDetails, setCurrentInvoice, addInvoiceFlag, resolveInvoiceFlag, loadRestaurantUsers
} from '../../../actions';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import api from '../../../api';
import Urls from '../../../api/urls';
import { parseUrl } from '../../../utils/StringFormatter';
import share from '../../../components/qubiqle/Share';
import RBSheet from '../../../components/qubiqle/RBSheet';
import MoreSheetItem from '../../../components/qubiqle/MoreSheetItem';

class InvoiceDetailContainer extends Component {
  static navigationOptions = ({ navigation }) => {
    let title = '';
    const { params } = navigation.state;
    let offsetInvoice = null;
    let handleBackPress = null;
    let showFlagAlert = null;
    let showMoreSheet = null;

    if (params) {
      title = params.title;
      offsetInvoice = params.offsetInvoice;
      handleBackPress = params.handleBackPress;
      showFlagAlert = params.showFlagAlert;
      showMoreSheet = params.showMoreSheet;
    }

    return {
      title,
      headerRight: (
        <View style={styles.headerButtons}>
          <TouchableOpacity onPress={() => {
            if (offsetInvoice) {
              offsetInvoice(-1);
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
            if (offsetInvoice) {
              offsetInvoice(1);
            }
          }}
          >
            <Image
              source={Images.down}
              style={styles.down}
              resizeMode="contain"
            />
          </TouchableOpacity>

          <TouchableOpacity onPress={() => {
            if (showFlagAlert) {
              showFlagAlert(true);
            }
          }}
          >
            <Image
              source={Images.flag}
              style={styles.flag}
              resizeMode="contain"
            />
          </TouchableOpacity>

          <TouchableOpacity onPress={() => {
            if (showMoreSheet) {
              showMoreSheet();
            }
          }}
          >
            <Image
              source={Images.more_vertical}
              style={styles.more_vertical}
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
    let { activeTab } = props.navigation.state.params;
    if (!activeTab) activeTab = 0;
    this.state = {
      index,
      type,
      restaurants: [],
      isReady: false,
      isShowFlagDialog: false,
      flagText: '',
      flagFormattedText: '',
      isLoading: false,
      currentTab: activeTab,
      activeTab
    };
  }

  async componentDidMount() {
    const restaurants = await Adapter.getRestaurants();
    this.setState({ restaurants });
    this.props.navigation.setParams({
      offsetInvoice: this.offsetInvoice,
      handleBackPress: this.handleBackPress,
      showFlagAlert: this.showFlagAlert,
      showMoreSheet: this.showMoreSheet
    });
    this.setInvoice();
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

  getInvoice() {
    const { index, type } = this.state;
    if (type === 'pending') return this.props.pendingInvoices.data[index];
    if (type === 'all') return this.props.allInvoices.data[index];
    return [];
  }

  setInvoice() {
    const { index, type } = this.state;
    let netLength = 0;

    if (type === 'pending') netLength = this.props.pendingInvoices.data.length;
    if (type === 'all') netLength = this.props.allInvoices.data.length;

    const title = `${index + 1} / ${netLength}`;
    this.props.navigation.setParams({ title });

    const invoice = this.getInvoice();
    this.setState({ invoice });
  }

  handleBackPress = () => {
    const popAction = StackActions.popToTop({ immediate: true });
    this.props.navigation.dispatch(popAction);
    return true;
  };

  offsetInvoice = async (offset) => {
    let { index } = this.state;
    const { type, activeTab } = this.state;
    let netLength = 0;

    let invoices = [];
    if (type === 'pending') invoices = this.props.pendingInvoices.data;
    if (type === 'all') invoices = this.props.allInvoices.data;

    netLength = invoices.length;
    index += offset;
    const canChange = !this.props.invoiceDetail.currentInvoice || this.props.invoiceDetail.currentInvoice === index - offset;

    if (index >= 0 && index < netLength && canChange) {
      this.props.setCurrentInvoice(index);
      const invoice = invoices[index];
      if (!invoice.line_items) {
        this.props.loadInvoiceDetails(invoice.id);
      }
      this.props.loadRestaurantUsers(invoice.restaurant);
      const title = `${index + 1} / ${netLength}`;
      this.props.navigation.push('InvoiceDetail', {
        type, index, offsetInvoice: this.offsetInvoice, title, activeTab
      });
    }
  };

  showFlagAlert = async (isShowFlagDialog) => {
    this.setState({ isShowFlagDialog });
  };

  showMoreSheet = () => {
    this.MoreSheet.open();
  };

  setFlagText = (flagText) => {
    this.setState({ flagText });
    this.setState({ flagFormattedText: flagText });
  };

  shareInvoice = async () => {
    this.setState({ isLoading: true });
    const { invoice } = this.state;
    const { id } = invoice;

    const {
      statusCode, data
    } = await api({
      method: 'GET',
      url: parseUrl(Urls.SHARE_TEXT_INVOICE, { invoice_id: id }),
    });

    if (statusCode === 200) {
      const options = await share(data);
      await this.setState({ isLoading: false });
      if (options) {
        setTimeout(() => {
          Share.open(options);
        }, 250);
      }
    } else {
      await this.setState({ isLoading: false });
    }
  };

  setCurrentTab = (currentTab) => {
    this.setState({ activeTab: currentTab });
  };

  goToInvoiceImage(image, index, count) {
    const { invoice, restaurants } = this.state;
    sendMixpanelEvent(MixpanelEvents.INVOICE_IMAGE_SELECTED, { image, index });
    this.props.navigation.navigate('InvoiceDetailImage', {
      image,
      index,
      count,
      invoice,
      restaurants
    });
  }

  renderMoreSheet() {
    const { invoice } = this.state;
    if (!invoice) return null;

    const data = [
      {
        icon: Images.flag,
        title: invoice.is_flagged ? 'Resolve Flag' : 'Flag Invoice',
        onPress: async () => {
          this.MoreSheet.close();
          setTimeout(() => {
            this.showFlagAlert(true);
          }, 350);
        }
      }, {
        icon: Images.icon_share,
        title: 'Share Invoice',
        onPress: () => {
          this.MoreSheet.close();
          setTimeout(() => {
            this.shareInvoice();
          }, 350);
        }
      }];

    return (
      <RBSheet
        closeOnDragDown
        ref={(ref) => {
          this.MoreSheet = ref;
        }}
        duration={300}
        height={250}
        customStyles={styles.moreSheet}
      >
        <View>
          {data.map((item) => (
            <MoreSheetItem
              item={item}
            />
          ))}
        </View>

        <MoreSheetItem
          item={{
            cancel: true,
            onPress: () => {
              this.MoreSheet.close();
            }
          }}
        />
      </RBSheet>
    );
  }

  render() {
    const {
      invoice, restaurants, isShowFlagDialog, flagText, isLoading, currentTab
    } = this.state;
    const goToInvoiceImage = this.goToInvoiceImage.bind(this);
    const { approveInvoice, addInvoiceFlag, resolveInvoiceFlag } = this.props;
    const { expandGlSplits, showInvoiceHistory } = this.props.userInfo;
    let users = [];
    if (invoice) users = this.props.restaurantUsers[invoice.restaurant];
    if (!users) users = [];

    if (!this.state.isReady) {
      return <View />;
    }

    return (
      <View style={styles.container}>
        <InvoiceDetail
          isLoading={isLoading}
          invoice={invoice}
          restaurants={restaurants}
          goToInvoiceImage={goToInvoiceImage}
          approveInvoice={approveInvoice}
          isShowFlagDialog={isShowFlagDialog}
          showFlagAlert={this.showFlagAlert}
          flagText={flagText}
          setFlagText={this.setFlagText}
          addInvoiceFlag={addInvoiceFlag}
          resolveInvoiceFlag={resolveInvoiceFlag}
          shareInvoice={this.shareInvoice}
          expandGlSplits={expandGlSplits}
          showInvoiceHistory={showInvoiceHistory}
          users={users}
          setCurrentTab={this.setCurrentTab}
          currentTab={currentTab}
        />
        {this.renderMoreSheet()}
      </View>
    );
  }
}

const mapStateToProps = (state) => ({
  pendingInvoices: state.pendingInvoices,
  allInvoices: state.allInvoices,
  invoiceDetail: state.invoiceDetail,
  userInfo: state.userInfo,
  restaurantUsers: state.restaurantUsers.data
});

export default connect(
  mapStateToProps,
  {
    loadLineItems, loadGlSplits, loadInvoiceImages, approveInvoice, loadInvoiceDetails, setCurrentInvoice, addInvoiceFlag, resolveInvoiceFlag, loadRestaurantUsers
  }
)(InvoiceDetailContainer);
