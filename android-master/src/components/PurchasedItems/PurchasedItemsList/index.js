import React from 'react';
import { FlatList } from 'react-native';
import Loader from '../../qubiqle/Loader';
import InvoiceEmpty from '../../qubiqle/InvoiceEmpty';
import PurchasedItem from '../PurchasedItem';

export default function PurchasedItemsList(props) {
  let {
    items
  } = props;
  const {
    loadNextPage, loading, firstLoad, onPress, style, emptyMessage, starItem, emptyView
  } = props;
  if (!items) items = [];

  return (
    <FlatList
      style={style}
      data={items}
      renderItem={({ item, index }) => (
        <PurchasedItem
          index={index}
          key={item.id.toString()}
          item={item}
          onPress={onPress}
          onStarMark={starItem}
        />
      )}
      onEndReached={() => loadNextPage()}
      ListFooterComponent={
        items.length
          ? (
            <Loader
              loading={loading}
            />
          ) : null
            }
      ListEmptyComponent={!loading && emptyView ? emptyView : (
        <InvoiceEmpty
          loading={loading}
          message={emptyMessage}
        />
      )}
      refreshing={items.length !== 0 && firstLoad}
      onRefresh={() => loadNextPage(1)}
      keyExtractor={(item) => item.id.toString()}
    />
  );
}
