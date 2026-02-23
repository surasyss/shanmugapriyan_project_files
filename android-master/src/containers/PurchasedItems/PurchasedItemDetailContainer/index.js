import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  BackHandler, Image, InteractionManager, TouchableOpacity, View
} from 'react-native';
import { StackActions } from 'react-navigation';
import { HeaderBackButton } from 'react-navigation-stack';
import {
  loadPurchasedItemDetails, setCurrentPurchasedItem, resetCategories, loadInvoiceDetailsStatic, markStar, deleteStar, markStarLocal
} from '../../../actions';
import styles from '../../Invoices/InvoiceDetailContainer/styles';
import Images from '../../../styles/Images';
import PurchasedItemDetail from '../../../components/PurchasedItems/PurchasedItemDetail';
import api from '../../../api';
import { parseUrl } from '../../../utils/StringFormatter';
import Urls from '../../../api/urls';
import showAlert from '../../../utils/QubiqleAlert';
import Adapter from '../../../utils/Adapter';

class PurchasedItemDetailContainer extends Component {
  static navigationOptions = ({ navigation }) => {
    let title = '';
    const { params } = navigation.state;
    let offsetItem = null;
    let handleBackPress = null;

    if (params) {
      title = params.title;
      offsetItem = params.offsetItem;
      handleBackPress = params.handleBackPress;
    }

    return {
      title,
      headerRight: (
        <View style={styles.headerButtons}>
          <TouchableOpacity onPress={() => {
            if (offsetItem) {
              offsetItem(-1);
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
            if (offsetItem) {
              offsetItem(1);
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
    let { activeTab } = props.navigation.state.params;
    if (!activeTab) activeTab = 0;
    this.state = {
      index,
      type,
      isReady: false,
      isLoading: false,
      currentTab: activeTab,
      activeTab,
      isAddingCategory: false,
      restaurantJson: {},
      isMounted: false
    };
  }

  async componentDidMount() {
    const restaurants = await Adapter.getRestaurants();
    const restaurantJson = {};
    if (restaurants) {
      restaurants.forEach((restaurant) => {
        restaurantJson[restaurant.id] = restaurant.name;
      });
    }
    this.setState({ restaurantJson, isMounted: true });
    this.props.navigation.setParams({
      offsetItem: this.offsetItem,
      handleBackPress: this.handleBackPress,
    });
    this.setItem();
    this.backHandler = BackHandler.addEventListener('hardwareBackPress', this.handleBackPress);

    InteractionManager.runAfterInteractions(() => {
      this.setState({
        isReady: true
      });
    });
  }

  // eslint-disable-next-line react/no-deprecated,no-unused-vars
  componentWillUpdate(nextProps, nextState, nextContext): void {
    return this.state !== nextState;
  }

  componentWillUnmount() {
    this.backHandler.remove();
    this.setState({ isMounted: false });
  }

  getItem() {
    const { index, type } = this.state;
    if (type === 'starred') return this.props.starredPurchasedItems.data[index];
    if (type === 'all') return this.props.allPurchasedItems.data[index];
    return [];
  }

  setItem() {
    const { index, type } = this.state;
    let netLength = 0;

    if (type === 'starred') netLength = this.props.starredPurchasedItems.data.length;
    if (type === 'all') netLength = this.props.allPurchasedItems.data.length;

    const title = `${index + 1} / ${netLength}`;
    this.props.navigation.setParams({ title });

    const item = this.getItem();
    this.setState({ item });
  }

  handleBackPress = () => {
    const popAction = StackActions.popToTop({ immediate: true });
    this.props.navigation.dispatch(popAction);
    return true;
  };

  offsetItem = async (offset) => {
    let { index } = this.state;
    const { type, activeTab } = this.state;
    let netLength = 0;

    let items = [];
    if (type === 'starred') items = this.props.starredPurchasedItems.data;
    if (type === 'all') items = this.props.allPurchasedItems.data;

    netLength = items.length;
    index += offset;
    const canChange = !this.props.purchasedItemDetail.currentItem || this.props.purchasedItemDetail.currentItem === index - offset;

    const { start_date, end_date } = this.props.navigation.state.params;

    if (index >= 0 && index < netLength && canChange) {
      this.props.setCurrentPurchasedItem(index);
      const item = items[index];
      if (!item.loaded) {
        this.props.loadPurchasedItemDetails(item.id, start_date, end_date);
      }
      const title = `${index + 1} / ${netLength}`;
      this.props.navigation.push('PurchasedItemDetail', {
        type,
        index,
        offsetItem: this.offsetItem,
        title,
        activeTab,
        start_date,
        end_date
      });
    }
  };

  setCurrentTab = (currentTab) => {
    this.setState({ activeTab: currentTab });
  };

  goToAddCategory = () => {
    let parent = null;
    const { item } = this.state;
    const { item_detail } = item;
    if (item_detail) {
      this.props.resetCategories();
      const { categories } = item_detail;
      if (categories.length) {
        parent = categories[categories.length - 1];
      }
    }
    this.props.navigation.push('CategoryPicker', { parent, onSelect: this.addCategory });
  };

  addCategory = async (category) => {
    this.setState({ isAddingCategory: true });
    const { item } = this.state;
    const { item_detail } = item;

    const categoryIds = item_detail.categories.map((c) => c.id);
    categoryIds.push(category.id);
    const {
      statusCode, errorMessage
    } = await api({
      method: 'PATCH',
      url: parseUrl(Urls.PURCHASED_ITEM, { item_id: item.id }),
      data: { categories: categoryIds }
    });

    if (statusCode === 200) {
      await this.props.loadPurchasedItemDetails(item.id);
      this.setState({ isAddingCategory: false });
    } else {
      await this.setState({ isAddingCategory: false });
      showAlert('Error', errorMessage);
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

  starItem = async () => {
    const { item } = this.state;
    const starred = !item.starred;

    await this.setState({ isLoading: true });
    let errorMessage = null;
    if (starred) {
      errorMessage = await markStar(item);
    } else {
      errorMessage = await deleteStar(item);
    }

    await this.setState({ isLoading: false });
    if (errorMessage) {
      showAlert('Error', errorMessage);
      return;
    }
    this.props.markStarLocal(item, starred);
  };

  render() {
    const {
      item, isAddingCategory, currentTab, restaurantJson, isLoading
    } = this.state;

    if (!this.state.isReady || !this.state.isMounted) {
      return <View />;
    }

    return (
      <PurchasedItemDetail
        item={item}
        currentTab={currentTab}
        restaurantJson={restaurantJson}
        goToAddCategory={this.goToAddCategory}
        setCurrentTab={this.setCurrentTab}
        loadInvoice={this.loadInvoice}
        isAddingCategory={isAddingCategory}
        isLoading={isLoading}
        onStarMark={this.starItem}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  starredPurchasedItems: state.starredPurchasedItems,
  allPurchasedItems: state.allPurchasedItems,
  purchasedItemDetail: state.purchasedItemDetail,
});

export default connect(
  mapStateToProps,
  {
    loadPurchasedItemDetails, setCurrentPurchasedItem, resetCategories, markStarLocal
  }
)(PurchasedItemDetailContainer);
