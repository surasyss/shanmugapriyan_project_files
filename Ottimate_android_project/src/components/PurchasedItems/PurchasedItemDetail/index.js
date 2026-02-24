import React from 'react';
import {
  View, Text, ScrollView, FlatList, TouchableOpacity, Image, Platform
} from 'react-native';
import { Chip } from 'react-native-paper';
import Modal from 'react-native-modal';
import ChartView from '../../qubiqle/Chart';
import styles from './styles';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import { roundTo, title, toCurrencyNoSpace } from '../../../utils/StringFormatter';
import Loader from '../../qubiqle/Loader';
import PurchasedItemInvoice from '../PurchasedItemInvoice';
import Colors from '../../../styles/Colors';
import { generateHighChartData } from './util';
import Images from '../../../styles/Images';
import ModalSelector from '../../qubiqle/ModalSelector';
import Spinner from '../../qubiqle/Spinner';

class PurchasedItemDetail extends React.Component {
  constructor(props) {
    super(props);
    let { currentTab } = this.props;
    if (!currentTab) currentTab = 0;
    this.state = {
      activeTab: currentTab,
      chartType: 'price',
      chartTypeName: 'Price',
      selectedValue: null,
      chartOptions: {}
    };
  }

  onTabSelection = (index) => {
    const { item, setCurrentTab } = this.props;
    if (index === 0) sendMixpanelEvent(MixpanelEvents.ITEMS_CHART_OPENED, { item });
    else if (index === 1) sendMixpanelEvent(MixpanelEvents.ITEMS_INVOICE_OPENED, { item });
    if (setCurrentTab) {
      setCurrentTab(index);
    }
  };

  onMessage = (message) => {
    const selected = JSON.parse(message.nativeEvent.data);
    if (selected) {
      this.setState({ selectedValue: selected });
    }
  };

  renderHeader() {
    const { item } = this.props;
    const {
      name, vendor_name, sku, primary_unit_name, pack_size_label
    } = item;

    return (
      <View style={styles.header}>
        <View style={styles.headerItem}>
          <Text style={styles.headerHeading}>Item Name</Text>
          <View style={styles.headerVendorName}>
            <Text style={[styles.headerValue, styles.headerLeft, name ? {} : styles.missingValue]}>{title(name)}</Text>
          </View>
        </View>

        <View style={styles.headerItem}>
          <Text style={styles.headerHeading}>Vendor Name</Text>
          <Text style={styles.headerValue}>{ vendor_name }</Text>
        </View>

        <View style={[styles.headerItem, styles.headerMultipleItems]}>
          <View style={styles.headerSku}>
            <Text style={styles.headerHeading}>Item SKU</Text>
            <Text style={styles.headerValue}>{sku || '--'}</Text>
          </View>

          <View style={styles.headerUnit}>
            <Text style={[styles.headerHeading, styles.centerText]}>Unit</Text>
            <Text style={[styles.headerValue, styles.centerText]}>{primary_unit_name || '--'}</Text>
          </View>

          <View style={styles.headerPackSize}>
            <Text style={[styles.headerHeading, styles.rightText]}>Pack Size</Text>
            <Text style={[styles.headerValue, styles.rightText]}>{pack_size_label || '--'}</Text>
          </View>
        </View>
        {this.renderCategories()}
      </View>
    );
  }

  renderCategories() {
    // const { item, goToAddCategory, isAddingCategory } = this.props;
    const { item } = this.props;
    const { item_detail } = item;
    if (item_detail) {
      const { categories } = item_detail;
      return (
        <View style={styles.headerCategory}>
          <Text style={styles.headerHeading}>Categories</Text>
          <View style={styles.categoriesView}>
            {categories.map((category) => (
              <Chip
                key={category.id.toString()}
                disabled
                style={styles.categoryChip}
                textStyle={styles.categoryText}
                mode="outlined"
              >
                {category.name}
              </Chip>
            ))}

            {/* {isAddingCategory ? <Loader loading /> : ( */}
            {/*  <Chip */}
            {/*    style={styles.addCategoryChip} */}
            {/*    textStyle={styles.addCategoryText} */}
            {/*    mode="outlined" */}
            {/*    onPress={() => { */}
            {/*      goToAddCategory(null); */}
            {/*    }} */}
            {/*  > */}
            {/*    Add Category */}
            {/*  </Chip> */}
            {/* )} */}
          </View>
        </View>
      );
    }
    return null;
  }

  renderTabs() {
    const tabs = ['Trend', 'Invoices'];
    return (
      <View style={[styles.tabs, this.props.style]}>
        {tabs.map((tab, i) => (
          <TouchableOpacity
            key={tab}
            onPress={() => {
              this.setState({ activeTab: i });
              this.onTabSelection(i);
            }}
            style={[styles.tab, { backgroundColor: this.state.activeTab === i ? 'rgb(255,255,255)' : 'rgb(236,241,247)' }]}
            activeOpacity={1}
          >
            <Text style={this.state.activeTab === i ? styles.tabTextSelected : styles.tabTextUnSelected}>
              {tab}
            </Text>
          </TouchableOpacity>
        ))}
        <TouchableOpacity
          onPress={() => {
            this.selector.open();
          }}
          style={[styles.tabSmall, { backgroundColor: 'rgb(236,241,247)' }]}
        >
          <Image
            source={Images.more_vertical}
            style={styles.more_vertical}
            resizeMode="contain"
          />
        </TouchableOpacity>
      </View>
    );
  }

  renderTabView() {
    if (this.state.activeTab === 0) {
      return this.renderChart();
    }
    return this.renderInvoices();
  }

  renderChart() {
    const { item, restaurantJson } = this.props;
    let { trend } = item;
    if (!trend) trend = [];
    if (trend.length === 0) {
      return (
        <View tabLabel="Invoices" style={styles.tabView}>
          <Text style={styles.textEmpty}>No data to display for this date range</Text>
        </View>
      );
    }

    const conf = generateHighChartData(trend, this.state.chartType, restaurantJson);

    const options = {
      global: {
        useUTC: false
      },
      lang: {
        decimalPoint: ',',
        thousandsSep: '.'
      }
    };

    return (
      <View tabLabel="Invoices" style={styles.tabView}>
        <ChartView
          style={styles.chart}
          config={conf}
          options={options}
          onMessage={(m) => this.onMessage(m)}
        />
      </View>
    );
  }

  renderInvoices() {
    const { item, restaurantJson, loadInvoice } = this.props;
    let { trend } = item;
    if (!trend) trend = [];
    let total_quantity = 0;
    let total_amount = 0;
    let average_price = 0;

    trend.forEach((invoice) => {
      total_quantity += invoice.quantity;
      total_amount += invoice.total_amount;
    });
    if (total_quantity !== 0) {
      average_price = total_amount / total_quantity;
    }

    if (trend.length === 0) {
      return (
        <View tabLabel="Invoices" style={styles.tabView}>
          <Text style={styles.textEmpty}>No data to display for this date range</Text>
        </View>
      );
    }

    return (
      <View tabLabel="Invoices" style={styles.tabView}>
        <FlatList
          scrollEnabled={false}
          data={trend}
          renderItem={({ item }) => (
            <PurchasedItemInvoice
              key={`${item.invoice_number.toString()}-${item.restaurant}-${item.date}-${item.quantity}`}
              item={item}
              restaurantJson={restaurantJson}
              onPress={() => {
                loadInvoice(item.invoice);
              }}
            />
          )}
          ListHeaderComponent={trend.length ? (
            <PurchasedItemInvoice
              heading
              index={0}
            />
          ) : null}
          ListFooterComponent={() => {
            if (trend.length > 0) {
              return (
                <View style={styles.footerContainer}>
                  <Text style={styles.footerItem}>{`Total Quantity: ${roundTo(total_quantity, 2)}`}</Text>
                  <Text style={styles.footerItem}>{`Average Price: ${toCurrencyNoSpace(average_price)}`}</Text>
                  <Text style={styles.footerItem}>{`Total Amount: ${toCurrencyNoSpace(total_amount)}`}</Text>
                </View>
              );
            }
            return null;
          }}
          keyExtractor={(item) => `${item.invoice_number.toString()}-${item.restaurant}-${item.date}-${item.quantity}`}
        />
      </View>
    );
  }

  renderTypeSelector() {
    const data = [
      { key: 'price', label: 'Price' },
      { key: 'quantity', label: 'Quantity' },
      { key: 'total_amount', label: 'Purchase Total' }
    ];

    return (
      <ModalSelector
        animationType="none"
        data={data}
        ref={(selector) => { this.selector = selector; }}
        initValueTextStyle={{ color: 'black' }}
        selectStyle={{ borderColor: 'black' }}
        selectTextStyle={{ color: 'blue' }}
        onChange={(option) => {
          this.setState({ chartType: option.key, chartTypeName: option.label });
        }}
      />
    );
  }

  renderChartInvoice() {
    const { restaurantJson, loadInvoice } = this.props;
    const { selectedValue } = this.state;

    if (selectedValue) {
      const {
        restaurant, invoice_number, date, quantity, price
      } = selectedValue;
      return (
        <Modal
          animationInTiming={1}
          animationOutTiming={1}
          isVisible={selectedValue ? true : null}
          backdropOpacity={0.5}
          onBackdropPress={() => this.setState({ selectedValue: null })}
          onRequestClose={() => this.setState({ selectedValue: null })}
        >

          <View style={styles.modal}>
            <Text style={styles.modalHeading}>{restaurantJson[restaurant]}</Text>
            <Text style={styles.modalValue}>{`Invoice: #${invoice_number}`}</Text>
            <Text style={styles.modalValue}>{`Date: ${date}`}</Text>
            <Text style={styles.modalValue}>{`Qty: ${quantity} @ ${toCurrencyNoSpace(price)}`}</Text>

            <TouchableOpacity
              style={styles.modalButton}
              onPress={async () => {
                const { invoice } = selectedValue;
                await this.setState({ selectedValue: null });
                loadInvoice(invoice);
              }}
            >
              <Text style={styles.modalButtonText}>
                Go to Invoice
              </Text>
            </TouchableOpacity>
          </View>
        </Modal>
      );
    }
    return null;
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
    const { item } = this.props;

    return (
      <ScrollView style={styles.scrollContainer}>
        <View style={styles.container}>
          {item ? this.renderHeader() : null}
          {item && item.loading ? (
            <View style={styles.header}>
              <Loader loading />
            </View>
          ) : (
            <View>
              {this.renderTabs()}
              {this.renderTabView()}
              {this.renderTypeSelector()}
              {this.renderChartInvoice()}
              {this.renderLoadingDialog()}
            </View>
          ) }

        </View>
      </ScrollView>
    );
  }
}

export default PurchasedItemDetail;
