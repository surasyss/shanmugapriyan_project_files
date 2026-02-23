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
import Adapter from '../../../utils/Adapter';
import {
  loadCreditRequestDetails, setCurrentCreditRequest, addCreditRequestFlag, resolveCreditRequestFlag, loadRestaurantUsers
} from '../../../actions';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import api from '../../../api';
import Urls from '../../../api/urls';
import { parseUrl } from '../../../utils/StringFormatter';
import share from '../../../components/qubiqle/Share';
import RBSheet from '../../../components/qubiqle/RBSheet';
import MoreSheetItem from '../../../components/qubiqle/MoreSheetItem';
import CreditRequestDetail from '../../../components/CreditRequests/CreditRequestDetail';

class CreditRequestDetailContainer extends Component {
  static navigationOptions = ({ navigation }) => {
    let title = '';
    const { params } = navigation.state;
    let offsetCreditRequest = null;
    let handleBackPress = null;
    let showFlagAlert = null;
    let showMoreSheet = null;

    if (params) {
      title = params.title;
      offsetCreditRequest = params.offsetCreditRequest;
      handleBackPress = params.handleBackPress;
      showFlagAlert = params.showFlagAlert;
      showMoreSheet = params.showMoreSheet;
    }

    return {
      title,
      headerRight: (
        <View style={styles.headerButtons}>
          <TouchableOpacity onPress={() => {
            if (offsetCreditRequest) {
              offsetCreditRequest(-1);
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
            if (offsetCreditRequest) {
              offsetCreditRequest(1);
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
      offsetCreditRequest: this.offsetCreditRequest,
      handleBackPress: this.handleBackPress,
      showFlagAlert: this.showFlagAlert,
      showMoreSheet: this.showMoreSheet
    });
    this.setCreditRequest();
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

  getCreditRequest() {
    const { index } = this.state;
    return this.props.allCreditRequests.data[index];
  }

  setCreditRequest() {
    const { index } = this.state;
    const netLength = this.props.allCreditRequests.data.length;

    const title = `${index + 1} / ${netLength}`;
    this.props.navigation.setParams({ title });

    const creditRequest = this.getCreditRequest();
    this.setState({ creditRequest });
  }

  handleBackPress = () => {
    const popAction = StackActions.popToTop({ immediate: true });
    this.props.navigation.dispatch(popAction);
    return true;
  };

  offsetCreditRequest = async (offset) => {
    let { index } = this.state;
    const { type, activeTab } = this.state;

    const creditRequests = this.props.allCreditRequests.data;
    const netLength = creditRequests.length;
    index += offset;
    const canChange = !this.props.creditRequestDetail.currentCreditRequest || this.props.creditRequestDetail.currentCreditRequest === index - offset;

    if (index >= 0 && index < netLength && canChange) {
      this.props.setCurrentCreditRequest(index);
      const creditRequest = creditRequests[index];
      if (!creditRequest.line_items) {
        this.props.loadCreditRequestDetails(creditRequest.id);
      }
      this.props.loadRestaurantUsers(creditRequest.restaurant);
      const title = `${index + 1} / ${netLength}`;
      this.props.navigation.push('CreditRequestDetail', {
        type, index, offsetCreditRequest: this.offsetCreditRequest, title, activeTab
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

  shareCreditRequest = async () => {
    this.setState({ isLoading: true });
    const { creditRequest } = this.state;
    const { id } = creditRequest;

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

  goToCreditRequestImage(image, index, count) {
    const { creditRequest, restaurants } = this.state;
    sendMixpanelEvent(MixpanelEvents.CREDIT_REQUEST_IMAGE_SELECTED, { image, index });
    this.props.navigation.navigate('InvoiceDetailImage', {
      image,
      index,
      count,
      invoice: creditRequest,
      restaurants
    });
  }

  renderMoreSheet() {
    const { creditRequest } = this.state;
    if (!creditRequest) return null;

    const data = [
      {
        key: 1,
        icon: Images.flag,
        title: creditRequest.is_flagged ? 'Resolve Flag' : 'Flag Credit Request',
        onPress: async () => {
          this.MoreSheet.close();
          setTimeout(() => {
            this.showFlagAlert(true);
          }, 350);
        }
      }, {
        key: 2,
        icon: Images.icon_share,
        title: 'Share Credit Request',
        onPress: () => {
          this.MoreSheet.close();
          setTimeout(() => {
            this.shareCreditRequest();
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
      creditRequest, restaurants, isShowFlagDialog, flagText, isLoading, currentTab
    } = this.state;
    const goToCreditRequestImage = this.goToCreditRequestImage.bind(this);
    const { addCreditRequestFlag, resolveCreditRequestFlag } = this.props;
    const { expandGlSplits, showInvoiceHistory } = this.props.userInfo;
    let users = [];
    if (creditRequest) users = this.props.restaurantUsers[creditRequest.restaurant];
    if (!users) users = [];

    if (!this.state.isReady) {
      return <View />;
    }

    return (
      <View style={styles.container}>
        <CreditRequestDetail
          isLoading={isLoading}
          creditRequest={creditRequest}
          restaurants={restaurants}
          goToCreditRequestImage={goToCreditRequestImage}
          isShowFlagDialog={isShowFlagDialog}
          showFlagAlert={this.showFlagAlert}
          flagText={flagText}
          setFlagText={this.setFlagText}
          addCreditRequestFlag={addCreditRequestFlag}
          resolveCreditRequestFlag={resolveCreditRequestFlag}
          shareInvoice={this.shareCreditRequest}
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
  allCreditRequests: state.allCreditRequests,
  creditRequestDetail: state.creditRequestDetail,
  userInfo: state.userInfo,
  restaurantUsers: state.restaurantUsers.data
});

export default connect(
  mapStateToProps,
  {
    loadCreditRequestDetails, setCurrentCreditRequest, addCreditRequestFlag, resolveCreditRequestFlag, loadRestaurantUsers
  }
)(CreditRequestDetailContainer);
