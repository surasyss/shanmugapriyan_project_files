import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  Image, TouchableOpacity, View, InteractionManager
} from 'react-native';
import Share from 'react-native-share';
import styles from './styles';
import Images from '../../../styles/Images';
import InvoiceDetail from '../../../components/Invoices/InvoiceDetail';
import Adapter from '../../../utils/Adapter';
import {
  approveInvoice, addInvoiceFlag, resolveInvoiceFlag, loadRestaurantUsers
} from '../../../actions';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import api from '../../../api';
import Urls from '../../../api/urls';
import { parseUrl } from '../../../utils/StringFormatter';
import share from '../../../components/qubiqle/Share';
import RBSheet from '../../../components/qubiqle/RBSheet';
import MoreSheetItem from '../../../components/qubiqle/MoreSheetItem';

class InvoiceDetailStaticContainer extends Component {
  static navigationOptions = ({ navigation }) => {
    let title = '';
    const { params } = navigation.state;
    let showFlagAlert = null;
    let showMoreSheet = null;

    if (params) {
      title = params.title;
      showFlagAlert = params.showFlagAlert;
      showMoreSheet = params.showMoreSheet;
    }

    return {
      title,
      headerRight: (
        <View style={styles.headerButtons}>
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
    };
  };

  constructor(props) {
    super(props);
    let { activeTab } = props.navigation.state.params;
    if (!activeTab) activeTab = 0;
    this.state = {
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
      showFlagAlert: this.showFlagAlert,
      showMoreSheet: this.showMoreSheet
    });
    this.setInvoice();
    InteractionManager.runAfterInteractions(() => {
      this.setState({
        isReady: true
      });
    });
  }

  setInvoice() {
    const { invoice } = this.props.navigation.state.params;
    this.setState({ invoice });
  }

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
    approveInvoice, addInvoiceFlag, resolveInvoiceFlag, loadRestaurantUsers
  }
)(InvoiceDetailStaticContainer);
