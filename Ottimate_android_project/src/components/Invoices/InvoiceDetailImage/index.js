import React from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, Image as RNImage, FlatList, BackHandler
} from 'react-native';
import ImageView from 'react-native-image-view';
import Image from 'react-native-image-progress';
import * as Progress from 'react-native-progress';
import { parserInvoiceDate } from '../../../utils/DateFormatter';
import styles from './styles';
import Images from '../../../styles/Images';
import { toCurrencyNoSpace } from '../../../utils/StringFormatter';

export default class InvoiceDetailImage extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      imageListVisible: false,
      imageVisible: false
    };
  }

  componentDidMount() {
    const { index } = this.props.navigation.state.params;

    const wait = new Promise((resolve) => setTimeout(resolve, 250));
    wait.then(() => {
      this.imageList.scrollToIndex({ index, animated: false });
      this.setState({ imageListVisible: true });
    });

    this.backHandler = BackHandler.addEventListener('hardwareBackPress', this.handleBackPress);
  }

  componentWillUnmount() {
    this.backHandler.remove();
  }

  handleBackPress = () => {
    this.props.navigation.goBack();
    return true;
  };

  renderHeader() {
    const { invoice, restaurants } = this.props.navigation.state.params;
    let vendor_name = '';
    const {
      vendor_obj, invoice_number, date, total_amount, is_vendor_supplied_invoice, is_flagged
    } = invoice;
    if (vendor_obj) vendor_name = vendor_obj.name;
    let restaurant_name = '';

    if (restaurants) {
      restaurants.forEach((restaurant) => {
        if (restaurant.id === invoice.restaurant) {
          restaurant_name = restaurant.name;
        }
      });
    }

    return (
      <View style={styles.header}>
        <View style={styles.headerItem}>
          <Text style={[styles.headerHeading, vendor_name ? {} : styles.missing]}>Vendor Name</Text>
          <View style={styles.headerVendorName}>
            <Text style={[styles.headerValue, styles.headerLeft, vendor_name ? {} : styles.missingValue]}>{vendor_name || 'Missing'}</Text>
            <View style={[styles.headerValue, styles.headerRight]}>
              {is_flagged
                ? (
                  <RNImage
                    resizeMode="contain"
                    source={Images.flag}
                    style={[styles.flag]}
                  />
                )
                : null}

              {is_vendor_supplied_invoice
                ? (
                  <RNImage
                    resizeMode="contain"
                    source={Images.mail_icon}
                    style={styles.email}
                  />
                )
                : null}
            </View>
          </View>
        </View>

        <View style={styles.headerItem}>
          <Text style={[styles.headerHeading, restaurant_name ? {} : styles.missing]}>Location Name</Text>
          <Text style={[styles.headerValue, restaurant_name ? {} : styles.missingValue]}>{restaurant_name || 'Missing'}</Text>
        </View>

        <View style={styles.lastHeaderItem}>
          <View style={styles.headerInvoiceNumber}>
            <Text style={[styles.headerHeading, invoice_number ? {} : styles.missing]}>Invoice Number</Text>
            <Text style={[styles.headerValue, invoice_number ? {} : styles.missingValue]}>{invoice_number || 'Missing'}</Text>
          </View>

          <View style={styles.headerInvoiceDate}>
            <Text style={[styles.headerHeading, styles.centerText, date ? {} : styles.missing]}>Invoice Date</Text>
            <Text style={[styles.headerValue, styles.centerText, date ? {} : styles.missingValue]}>{parserInvoiceDate(date) || 'Missing'}</Text>
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

  renderModal() {
    const { imageVisible, index } = this.state;
    const { invoice } = this.props.navigation.state.params;

    let invoiceImages = invoice.images;
    if (!invoiceImages) invoiceImages = [];
    const images = invoiceImages.map((image) => ({
      source: image.optimized_url ? { uri: image.optimized_url } : { uri: image.url }
    }));

    return (
      <ImageView
        images={images}
        imageIndex={index}
        isVisible={imageVisible}
        onClose={() => this.setState({ imageVisible: false })}
      />
    );
  }

  render() {
    const {
      count, invoice
    } = this.props.navigation.state.params;
    const { imageListVisible } = this.state;

    let invoiceImages = invoice.images;
    if (!invoiceImages) invoiceImages = [];

    return (
      <ScrollView
        contentContainerStyle={styles.containerStyle}
        style={styles.container}
      >

        <FlatList
          style={!imageListVisible ? { opacity: 0 } : {}}
          ref={(ref) => { this.imageList = ref; }}
          horizontal
          pagingEnabled
          data={invoiceImages}
          renderItem={({ item, index }) => (
            <View style={styles.imageContainer}>
              <TouchableOpacity
                onPress={() => { this.setState({ imageVisible: true, index }); }}
              >
                <Image
                  source={item.optimized_url ? { uri: item.optimized_url } : { uri: item.url }}
                  style={styles.image}
                  resizeMode="contain"
                  indicator={(
                    <Progress.Circle
                      size={30}
                      indeterminate
                    />
                      )}
                />

                <View style={styles.waterMarkView}>
                  <Text style={styles.waterMark}>
                    {index + 1}
                    /
                    {count}
                  </Text>
                </View>

              </TouchableOpacity>
            </View>
          )}
          keyExtractor={(item) => item.optimized_url}
          listKey={(item, index) => index.toString()}
          showsHorizontalScrollIndicator={false}
        />

        <View style={styles.bottomContainer}>
          {this.renderHeader()}
        </View>

        {this.renderModal()}
      </ScrollView>
    );
  }
}
